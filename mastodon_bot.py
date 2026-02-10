#!/usr/bin/env python3
"""
Mastodon repost bot with like functionality
Automatically reposts new posts from specified accounts
Likes posts based on configuration
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set, Optional

import yaml
from dotenv import load_dotenv
from mastodon import Mastodon, MastodonAPIError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class MastodonRepostBot:
    """Mastodon bot that automatically reposts, likes and follows back"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the bot

        Args:
            config_path: path to the repost configuration file
        """
        self.config = self._load_config(config_path)
        self.mastodon = self._init_mastodon()
        
        # Track processed posts
        self.processed_posts: Set[str] = set()
        self.liked_posts: Set[str] = set()
        self.followed_accounts: Set[str] = set()
        self.processed_file = "processed_posts.json"
        self.liked_file = "liked_posts.json"
        self.followed_file = "followed_accounts.json"
        self._load_processed_posts()
        self._load_liked_posts()
        self._load_followed_accounts()
        
        # Repost settings
        self.accounts_to_monitor = self.config['accounts_to_monitor']
        self.check_interval = self.config['bot']['check_interval']
        self.boost_only = self.config['bot'].get('boost_only', False)
        self.exclude_replies = self.config['bot'].get('exclude_replies', False)
        self.exclude_reblogs = self.config['bot'].get('exclude_reblogs', False)
        
        # Like settings (now read from the single config.yaml)
        self.like_accounts = self.config.get('likes', [])
        self.like_settings = self.config.get('like_settings', {})
        self.max_likes_per_check = self.like_settings.get('max_likes_per_check', 50)
        
        # Follow-back settings
        self.enable_follow_back = self.config['bot'].get('follow_back', False)
        
        logger.info(f"Bot initialisiert für {len(self.accounts_to_monitor)} Repost-Accounts")
        logger.info(f"Like-Konfiguration für {len(self.like_accounts)} Accounts geladen")
        if self.enable_follow_back:
            logger.info("Follow-back Funktion aktiviert")
    
    def _load_config(self, config_path: str) -> dict:
        """Konfigurationsdatei laden"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configuration loaded: {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error loading YAML file: {e}")
            raise
    
    def _init_mastodon(self) -> Mastodon:
        """Mastodon-Client initialisieren"""
        access_token = os.getenv('MASTODON_ACCESS_TOKEN')
        instance_url = os.getenv('MASTODON_INSTANCE_URL')
        
        # Fallback auf Config-Datei wenn nicht in .env
        if not instance_url and 'mastodon' in self.config:
            instance_url = self.config['mastodon'].get('instance_url', 'https://mastodon.social')
        elif not instance_url:
            instance_url = 'https://mastodon.social'
        
        if not access_token:
            logger.error("MASTODON_ACCESS_TOKEN nicht in .env definiert")
            raise ValueError("Access Token fehlt")
        
        mastodon = Mastodon(
            access_token=access_token,
            api_base_url=instance_url
        )
        
        logger.info(f"Mit {instance_url} verbunden")
        return mastodon
    
    def _load_processed_posts(self):
        """Load already processed (reposted) posts"""
        if Path(self.processed_file).exists():
            try:
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    self.processed_posts = set(data.get('posts', []))
                logger.info(f"{len(self.processed_posts)} processed (reposted) posts loaded")
            except json.JSONDecodeError:
                logger.warning("Could not deserialize processed_posts.json")
                self.processed_posts = set()
    
    def _load_liked_posts(self):
        """Load already liked posts"""
        if Path(self.liked_file).exists():
            try:
                with open(self.liked_file, 'r') as f:
                    data = json.load(f)
                    self.liked_posts = set(data.get('posts', []))
                logger.info(f"{len(self.liked_posts)} liked posts loaded")
            except json.JSONDecodeError:
                logger.warning("Could not deserialize liked_posts.json")
                self.liked_posts = set()
    
    def _save_processed_posts(self):
        """Save reposted posts"""
        with open(self.processed_file, 'w') as f:
            json.dump({'posts': list(self.processed_posts)}, f)
    
    def _save_liked_posts(self):
        """Save liked posts"""
        with open(self.liked_file, 'w') as f:
            json.dump({'posts': list(self.liked_posts)}, f)
    
    def _load_followed_accounts(self):
        """Load already followed accounts"""
        if Path(self.followed_file).exists():
            try:
                with open(self.followed_file, 'r') as f:
                    data = json.load(f)
                    self.followed_accounts = set(data.get('accounts', []))
                logger.info(f"{len(self.followed_accounts)} already-followed accounts loaded")
            except json.JSONDecodeError:
                logger.warning("Could not deserialize followed_accounts.json")
                self.followed_accounts = set()
    
    def _save_followed_accounts(self):
        """Save followed accounts"""
        with open(self.followed_file, 'w') as f:
            json.dump({'accounts': list(self.followed_accounts)}, f)
    
    def _get_account_id(self, account_handle: str) -> Optional[str]:
        """Query account ID from handle"""
        try:
            results = self.mastodon.account_search(account_handle, limit=1)
            if results:
                account_id = results[0]['id']
                logger.debug(f"Account {account_handle} -> ID {account_id}")
                return str(account_id)
            else:
                logger.warning(f"Account nicht gefunden: {account_handle}")
                return None
        except MastodonAPIError as e:
            logger.error(f"Fehler bei Account-Suche {account_handle}: {e}")
            return None
    
    def _should_repost(self, status: dict) -> bool:
        """Check if a post should be reposted"""
        # Exclude replies?
        if self.exclude_replies and status.get('in_reply_to_id'):
            return False
        # Exclude reblogs?
        if self.exclude_reblogs and status.get('reblog'):
            return False
        # If boost_only: only media posts
        if self.boost_only and not status.get('media_attachments'):
            return False
        
        return True
    
    def _extract_hashtags(self, status: dict) -> Set[str]:
        """Extract hashtags from a status"""
        tags = set()
        for tag in status.get('tags', []):
            tags.add(tag['name'].lower())
        return tags
    
    def _should_like(self, status: dict, like_config: dict) -> bool:
        """Decide whether a status should be liked"""
        # Like everything?
        if like_config.get('like_everything', False):
            return True
        # Exclude replies?
        if like_config.get('exclude_replies', False) and status.get('in_reply_to_id'):
            return False
        # Require media?
        if like_config.get('require_media', False) and not status.get('media_attachments'):
            return False
        # Hashtag filter
        required_hashtags = like_config.get('hashtags', [])
        if required_hashtags:
            status_hashtags = self._extract_hashtags(status)
            # Mindestens einen erforderlichen Hashtag haben?
            # At least one required hashtag?
            if not any(tag.lower() in status_hashtags for tag in required_hashtags):
                return False
        
        return True
    
    def _repost_status(self, status: dict) -> bool:
        """Repost a status"""
        status_id = str(status['id'])
        
        # Already processed?
        if status_id in self.processed_posts:
            logger.debug(f"Post {status_id} already reposted")
            return False
        
        # Sollte gepostet werden?
        if not self._should_repost(status):
            logger.debug(f"Post {status_id} erfüllt Bedingungen nicht")
            return False
        
        try:
            # Status rebloggen (auf Mastodon: "boost")
            self.mastodon.status_reblog(status_id)
            self.processed_posts.add(status_id)
            self._save_processed_posts()
            
            author = status['account']['acct']
            content_preview = status['content'][:100]
            # Remove HTML tags and unescape
            import html
            content_preview = html.unescape(content_preview).replace('<p>', '').replace('</p>', '').replace('<br/>', '').replace('<br>', '')
            logger.info(f"✓ Reposted from @{author}: {content_preview}...")
            
            return True
        except MastodonAPIError as e:
            logger.error(f"Error reposting {status_id}: {e}")
            return False
    
    def _like_status(self, status: dict) -> bool:
        """Like a status"""
        status_id = str(status['id'])
        
        # Already liked?
        if status_id in self.liked_posts:
            logger.debug(f"Post {status_id} already liked")
            return False
        
        try:
            self.mastodon.status_favourite(status_id)
            self.liked_posts.add(status_id)
            self._save_liked_posts()
            
            author = status['account']['acct']
            content_preview = status['content'][:80]
            # Remove HTML tags and unescape
            import html
            content_preview = html.unescape(content_preview).replace('<p>', '').replace('</p>', '').replace('<br/>', '').replace('<br>', '')
            logger.info(f"♥ Liked from @{author}: {content_preview}...")
            
            return True
        except MastodonAPIError as e:
            logger.error(f"Error liking {status_id}: {e}")
            return False
    
    def check_new_posts(self):
        """Check new posts from monitored accounts"""
        logger.info("Checking for new posts...")
        
        for account_handle in self.accounts_to_monitor:
            account_id = self._get_account_id(account_handle)
            if not account_id:
                continue
            
            try:
                # Letzte Posts abrufen
                statuses = self.mastodon.account_statuses(
                    account_id,
                    limit=20,
                    exclude_replies=self.exclude_replies,
                    exclude_reblogs=self.exclude_reblogs
                )
                
                reposted_count = 0
                for status in statuses:
                    if self._repost_status(status):
                        reposted_count += 1
                
                if reposted_count > 0:
                    logger.info(f"@{account_handle}: {reposted_count} new posts reposted")
                
            except MastodonAPIError as e:
                logger.error(f"Error fetching @{account_handle}: {e}")
    
    def check_likes(self):
        """Check new posts for liking"""
        if not self.like_accounts:
            return

        logger.info("Checking for new posts to like...")
        liked_count = 0
        
        for like_config in self.like_accounts:
            account_handle = like_config['account']
            account_id = self._get_account_id(account_handle)
            
            if not account_id:
                continue
            
            # Limit überschritten?
            if liked_count >= self.max_likes_per_check:
                logger.info(f"Like-Limit ({self.max_likes_per_check}) erreicht")
                break
            
            try:
                # Letzte Posts abrufen
                exclude_replies = like_config.get('exclude_replies', False)
                statuses = self.mastodon.account_statuses(
                    account_id,
                    limit=20,
                    exclude_replies=exclude_replies
                )
                
                for status in statuses:
                    if liked_count >= self.max_likes_per_check:
                        break
                    
                    if self._should_like(status, like_config):
                        if self._like_status(status):
                            liked_count += 1
                
            except MastodonAPIError as e:
                logger.error(f"Error fetching @{account_handle}: {e}")
        
        if liked_count > 0:
            logger.info(f"In total {liked_count} posts liked")
    
    def check_follow_back(self):
        """Follow back new followers in order"""
        if not self.enable_follow_back:
            return

        logger.info("Checking for new followers...")
        try:
            # Hole die Liste der eigenen Follower
            me_id = self.mastodon.me()['id']
            followers = self.mastodon.account_followers(me_id, limit=40)
            
            if not followers:
                logger.debug("No followers found or already all followed")
                return
            
            followed_count = 0
            for follower in followers:
                account_id = str(follower['id'])
                account_acct = follower['acct']
                
                # Already followed?
                if account_id in self.followed_accounts:
                    continue
                
                try:
                    # Account folgen
                    self.mastodon.account_follow(account_id)
                    self.followed_accounts.add(account_id)
                    self._save_followed_accounts()
                    
                    logger.info(f"✓ Followed back: @{account_acct}")
                    followed_count += 1
                except MastodonAPIError as e:
                    logger.error(f"Error following @{account_acct}: {e}")
            
            if followed_count > 0:
                logger.info(f"Insgesamt {followed_count} neue Accounts gef\u00f6lgt")
        
        except MastodonAPIError as e:
            logger.error(f"Error fetching followers: {e}")
    
    def run(self):
        """Bot im Schleifenmodus starten"""
        logger.info("Bot running. Press Ctrl+C to stop.")
        try:
            while True:
                self.check_new_posts()
                self.check_likes()
                self.check_follow_back()
                logger.debug(f"Nächste Prüfung in {self.check_interval} Sekunden")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Bot beendet")
        except Exception as e:
            logger.error(f"Kritischer Fehler: {e}")
            raise


def main():
    """Main entry point"""
    bot = MastodonRepostBot()
    bot.run()


if __name__ == "__main__":
    main()
