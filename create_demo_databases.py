#!/usr/bin/env python3
"""
Create realistic demo WhatsApp databases for GitHub demonstration
This creates fake but realistic-looking WhatsApp data for testing purposes
"""

import sqlite3
import random
from datetime import datetime, timedelta

def create_demo_msgstore():
    """Create a realistic demo msgstore.db"""
    
    conn = sqlite3.connect('demo_msgstore.db')
    cursor = conn.cursor()
    
    # Create tables with modern WhatsApp schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat (
            _id INTEGER PRIMARY KEY,
            jid_row_id INTEGER,
            hidden INTEGER DEFAULT 0,
            subject TEXT,
            created_timestamp INTEGER,
            display_message_row_id INTEGER,
            last_message_row_id INTEGER,
            last_read_message_row_id INTEGER,
            last_read_receipt_sent_message_row_id INTEGER,
            last_important_message_row_id INTEGER,
            archived INTEGER DEFAULT 0,
            sort_timestamp INTEGER,
            mod_tag INTEGER,
            gen INTEGER,
            spam_detection_enabled INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jid (
            _id INTEGER PRIMARY KEY,
            user TEXT,
            server TEXT,
            agent INTEGER,
            device INTEGER,
            type INTEGER,
            raw_string TEXT UNIQUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message (
            _id INTEGER PRIMARY KEY,
            chat_row_id INTEGER,
            from_me INTEGER,
            key_id TEXT,
            sender_jid_row_id INTEGER,
            status INTEGER,
            broadcast INTEGER,
            recipient_count INTEGER,
            participant_hash TEXT,
            originator_device_timestamp INTEGER,
            timestamp INTEGER,
            sort_id INTEGER,
            message_type INTEGER,
            text_data TEXT,
            starred INTEGER DEFAULT 0,
            lookup_tables INTEGER,
            message_add_on_flags INTEGER,
            view_mode INTEGER,
            read_receipt_policy INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_media (
            message_row_id INTEGER PRIMARY KEY,
            chat_row_id INTEGER,
            autotransfer_retry_enabled INTEGER,
            multicast_id TEXT,
            media_job_uuid TEXT,
            transferred INTEGER,
            transcoded INTEGER,
            file_path TEXT,
            file_size INTEGER,
            suspicious_content INTEGER,
            trim_from INTEGER,
            trim_to INTEGER,
            face_x INTEGER,
            face_y INTEGER,
            media_key BLOB,
            media_key_timestamp INTEGER,
            width INTEGER,
            height INTEGER,
            has_streaming_sidecar INTEGER,
            gif_attribution INTEGER,
            thumbnail_height_width_ratio REAL,
            direct_path TEXT,
            first_scan_sidecar BLOB,
            first_scan_length INTEGER,
            message_url TEXT,
            mime_type TEXT,
            file_length INTEGER,
            media_name TEXT,
            file_hash TEXT,
            media_duration INTEGER,
            page_count INTEGER,
            enc_file_hash TEXT,
            partial_media_hash TEXT,
            partial_media_enc_hash TEXT,
            is_animated_sticker INTEGER
        )
    ''')
    
    # Sample contact names and numbers
    contacts = [
        ("Alice Johnson", "1234567890"),
        ("Bob Smith", "2345678901"),
        ("Charlie Brown", "3456789012"),
        ("Diana Prince", "4567890123"),
        ("Eve Wilson", "5678901234"),
        ("Frank Castle", "6789012345"),
        ("Grace Kelly", "7890123456"),
        ("Henry Ford", "8901234567"),
    ]
    
    # Sample messages for realistic conversations
    message_templates = {
        'greeting': ["Hey! How are you?", "Hi there!", "Good morning!", "What's up?", "Hello!"],
        'response': ["I'm good, thanks!", "Pretty good! You?", "All good here", "Doing well!", "Great!"],
        'question': ["Did you see that?", "Are you free tomorrow?", "Want to grab coffee?", "Can you help me with something?"],
        'emoji': ["😂😂😂", "👍", "❤️", "🎉🎉", "😊", "🔥", "💯"],
        'casual': ["That's awesome!", "No way!", "Really?", "Interesting...", "I see", "Cool!", "Nice!"],
        'media_caption': ["Check this out!", "Look at this!", "😍", "Wow!", "Amazing!"],
    }
    
    # Create JIDs for contacts
    jid_map = {}
    for idx, (name, number) in enumerate(contacts):
        jid_string = f"{number}@s.whatsapp.net"
        cursor.execute('''
            INSERT OR IGNORE INTO jid (_id, user, server, agent, device, type, raw_string)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (idx + 1, number, "s.whatsapp.net", 0, 0, 0, jid_string))
        jid_map[idx + 1] = (name, number, jid_string)
    
    # Create chats
    for jid_id in range(1, len(contacts) + 1):
        cursor.execute('''
            INSERT INTO chat (_id, jid_row_id, hidden, archived, sort_timestamp)
            VALUES (?, ?, 0, 0, ?)
        ''', (jid_id, jid_id, int(datetime.now().timestamp() * 1000)))
    
    # Create realistic messages
    message_id = 1
    base_time = datetime.now() - timedelta(days=90)  # Start 90 days ago
    
    for chat_id in range(1, len(contacts) + 1):
        # Each contact gets 15-50 messages
        num_messages = random.randint(15, 50)
        conversation_time = base_time + timedelta(days=random.randint(0, 80))
        
        for msg_idx in range(num_messages):
            # Simulate conversation flow
            from_me = random.choice([0, 1])
            
            # Choose message type (0=text, 1=image, 2=audio, 3=video, etc.)
            msg_type = random.choices(
                [0, 1, 2, 3, 20],  # text, image, audio, video, sticker
                weights=[70, 15, 5, 5, 5]
            )[0]
            
            # Generate message text
            if msg_type == 0:  # Text message
                category = random.choice(list(message_templates.keys()))
                text = random.choice(message_templates[category])
            else:
                text = random.choice(message_templates['media_caption']) if random.random() > 0.5 else None
            
            timestamp = int((conversation_time + timedelta(hours=msg_idx * random.uniform(0.5, 8))).timestamp() * 1000)
            
            cursor.execute('''
                INSERT INTO message (_id, chat_row_id, from_me, key_id, sender_jid_row_id, 
                                   status, message_type, text_data, sort_id, timestamp, originator_device_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (message_id, chat_id, from_me, f"KEY{message_id}", chat_id if from_me == 0 else None,
                  5, msg_type, text, message_id, timestamp, timestamp))
            
            # Add media info if not a text message
            if msg_type != 0:
                mime_types = {
                    1: 'image/jpeg',
                    2: 'audio/ogg; codecs=opus',
                    3: 'video/mp4',
                    20: 'image/webp'
                }
                cursor.execute('''
                    INSERT INTO message_media (message_row_id, chat_row_id, mime_type, file_size)
                    VALUES (?, ?, ?, ?)
                ''', (message_id, chat_id, mime_types.get(msg_type, 'application/octet-stream'), 
                      random.randint(50000, 5000000)))
            
            message_id += 1
    
    conn.commit()
    conn.close()
    print(f"✅ Created demo_msgstore.db with {message_id-1} messages")


def create_demo_wa():
    """Create a realistic demo wa.db"""
    
    conn = sqlite3.connect('demo_wa.db')
    cursor = conn.cursor()
    
    # Create jid table first (for mapping)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jid (
            _id INTEGER PRIMARY KEY,
            user TEXT,
            server TEXT,
            agent INTEGER,
            device INTEGER,
            type INTEGER,
            raw_string TEXT UNIQUE
        )
    ''')
    
    # Create jid_map table for LID mapping
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jid_map (
            _id INTEGER PRIMARY KEY,
            lid_row_id INTEGER,
            jid_row_id INTEGER,
            UNIQUE(lid_row_id, jid_row_id)
        )
    ''')
    
    # Create wa_contacts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wa_contacts (
            _id INTEGER PRIMARY KEY,
            jid TEXT UNIQUE,
            is_whatsapp_user INTEGER,
            status TEXT,
            status_timestamp INTEGER,
            number TEXT,
            raw_contact_id INTEGER,
            display_name TEXT,
            phone_type INTEGER,
            phone_label TEXT,
            unseen_msg_count INTEGER,
            photo_ts INTEGER,
            thumb_ts INTEGER,
            photo_id_timestamp INTEGER,
            given_name TEXT,
            family_name TEXT,
            wa_name TEXT,
            sort_name TEXT,
            nickname TEXT,
            company TEXT,
            title TEXT
        )
    ''')
    
    # Sample contacts
    contacts = [
        ("Alice Johnson", "Alice", "Johnson", "1234567890@s.whatsapp.net", "1234567890", "Hey there! Using WhatsApp"),
        ("Bob Smith", "Bob", "Smith", "2345678901@s.whatsapp.net", "2345678901", "Busy"),
        ("Charlie Brown", "Charlie", "Brown", "3456789012@s.whatsapp.net", "3456789012", "Available"),
        ("Diana Prince", "Diana", "Prince", "4567890123@s.whatsapp.net", "4567890123", "At work"),
        ("Eve Wilson", "Eve", "Wilson", "5678901234@s.whatsapp.net", "5678901234", "💼 Working..."),
        ("Frank Castle", "Frank", "Castle", "6789012345@s.whatsapp.net", "6789012345", "🎮 Gaming"),
        ("Grace Kelly", "Grace", "Kelly", "7890123456@s.whatsapp.net", "7890123456", "✈️ Traveling"),
        ("Henry Ford", "Henry", "Ford", "8901234567@s.whatsapp.net", "8901234567", "Available"),
    ]
    
    # First insert into jid table
    for idx, (_, _, _, jid, number, _) in enumerate(contacts):
        cursor.execute('''
            INSERT INTO jid (_id, user, server, type, raw_string)
            VALUES (?, ?, ?, ?, ?)
        ''', (idx + 1, number, "s.whatsapp.net", 0, jid))
    
    # Insert contacts
    for idx, (display_name, given_name, family_name, jid, number, status) in enumerate(contacts):
        cursor.execute('''
            INSERT INTO wa_contacts (_id, jid, is_whatsapp_user, status, number, display_name, 
                                   given_name, family_name, wa_name, sort_name)
            VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
        ''', (idx + 1, jid, status, number, display_name, given_name, family_name, given_name, display_name))
    
    # Populate jid_map (mapping LID to normal JID - in this demo they're the same)
    for idx in range(1, len(contacts) + 1):
        cursor.execute('''
            INSERT INTO jid_map (_id, lid_row_id, jid_row_id)
            VALUES (?, ?, ?)
        ''', (idx, idx, idx))
    
    conn.commit()
    conn.close()
    print(f"✅ Created demo_wa.db with {len(contacts)} contacts")


if __name__ == '__main__':
    print("🔨 Creating demo WhatsApp databases...")
    print("=" * 60)
    create_demo_msgstore()
    create_demo_wa()
    print("=" * 60)
    print("✅ Demo databases created successfully!")
    print("\n📝 You can now test with:")
    print("   python3 main.py demo_msgstore.db -w demo_wa.db -o demo_report.html")

