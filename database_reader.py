"""
WhatsApp Veritabanı Okuyucu Modülü
msgstore.db ve wa.db dosyalarını okur ve işler
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os


class WhatsAppDatabaseReader:
    """WhatsApp veritabanlarını okuma ve işleme sınıfı"""
    
    def __init__(self, msgstore_path, wa_db_path=None):
        """
        Args:
            msgstore_path: msgstore.db dosya yolu
            wa_db_path: wa.db dosya yolu (opsiyonel)
        """
        self.msgstore_path = msgstore_path
        self.wa_db_path = wa_db_path
        self.msgstore_conn = None
        self.wa_conn = None
        self.lid_map_df = None
        
    def connect(self):
        """Veritabanlarına bağlan"""
        try:
            if os.path.exists(self.msgstore_path):
                self.msgstore_conn = sqlite3.connect(self.msgstore_path)
                print(f"✅ msgstore.db bağlantısı başarılı")
            else:
                raise FileNotFoundError(f"msgstore.db bulunamadı: {self.msgstore_path}")
                
            if self.wa_db_path and os.path.exists(self.wa_db_path):
                self.wa_conn = sqlite3.connect(self.wa_db_path)
                print(f"✅ wa.db bağlantısı başarılı")
            else:
                print(f"⚠️ wa.db bulunamadı, grup analizi sınırlı olacak")
                
        except Exception as e:
            print(f"❌ Veritabanı bağlantı hatası: {e}")
            raise
    
    def close(self):
        """Veritabanı bağlantılarını kapat"""
        if self.msgstore_conn:
            self.msgstore_conn.close()
        if self.wa_conn:
            self.wa_conn.close()
    
    def get_messages(self):
        """Tüm mesajları çek"""
        try:
            # Önce sender_jid_row_id sütununun olup olmadığını kontrol et
            cursor = self.msgstore_conn.cursor()
            cursor.execute("PRAGMA table_info(message)")
            columns = [col[1] for col in cursor.fetchall()]
            has_sender_jid = 'sender_jid_row_id' in columns
            
            # Modern WhatsApp veritabanı yapısı (normalizeli)
            if has_sender_jid:
                query = """
                SELECT 
                    m._id as message_id,
                    m.chat_row_id,
                    m.from_me,
                    m.timestamp,
                    m.text_data as message_text,
                    m.message_type,
                    m.status,
                    j.raw_string as chat_jid,
                    sender_j.raw_string as sender_jid
                FROM message AS m
                LEFT JOIN chat AS c ON m.chat_row_id = c._id
                LEFT JOIN jid AS j ON c.jid_row_id = j._id
                LEFT JOIN jid AS sender_j ON m.sender_jid_row_id = sender_j._id
                WHERE m.chat_row_id > 0
                ORDER BY m.timestamp ASC
                """
            else:
                # Basit versiyon (sender_jid_row_id yok)
                query = """
                SELECT 
                    m._id as message_id,
                    m.chat_row_id,
                    m.from_me,
                    m.timestamp,
                    m.text_data as message_text,
                    m.message_type,
                    m.status,
                    j.raw_string as chat_jid
                FROM message AS m
                LEFT JOIN chat AS c ON m.chat_row_id = c._id
                LEFT JOIN jid AS j ON c.jid_row_id = j._id
                WHERE m.chat_row_id > 0
                ORDER BY m.timestamp ASC
                """
            
            df = pd.read_sql_query(query, self.msgstore_conn)
            
            # Timestamp'i datetime'a çevir (milisaniye cinsinden)
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
            
            # Chat türünü belirle (grup mu, kişisel mi)
            df['is_group'] = df['chat_jid'].str.contains('@g.us', na=False)
            df['chat_id'] = df['chat_jid']  # Uyumluluk için
            
            # Medya bilgisini message_type'dan çıkar
            df['media_type'] = df['message_type'].apply(self._map_message_type_to_media)
            
            # from_me bilgisini kontrol et ve logla
            if 'from_me' in df.columns:
                sent_count = (df['from_me'] == 1).sum()
                received_count = (df['from_me'] == 0).sum()
                print(f"✅ {len(df)} mesaj yüklendi (Gönderilen: {sent_count}, Alınan: {received_count})")
            else:
                print(f"✅ {len(df)} mesaj yüklendi")
            
            return df
            
        except Exception as e:
            print(f"❌ Mesaj okuma hatası: {e}")
            print(f"   Hata detayı: {str(e)}")
            return pd.DataFrame()
    
    def _map_message_type_to_media(self, msg_type):
        """Message type'ı medya türüne çevir"""
        if pd.isna(msg_type):
            return 0  # Text
        
        # WhatsApp message_type kodları
        type_map = {
            0: 0,   # Text
            1: 1,   # Image
            2: 2,   # Audio/Voice
            3: 3,   # Video
            4: 4,   # Contact
            5: 5,   # Location
            7: 9,   # Document
            8: 2,   # Audio
            9: 9,   # Document
            13: 13, # GIF
            14: 2,  # Voice note
            15: 1,  # Image
            20: 20, # Sticker
            26: 3,  # Video note
            42: 9,  # Product
            43: 9,  # Order
        }
        
        return type_map.get(int(msg_type), 0)
    
    def get_contacts(self):
        """Kişi listesini çek"""
        try:
            # wa.db'den kişileri çek
            if self.wa_conn:
                query = """
                SELECT 
                    jid,
                    display_name,
                    given_name,
                    status
                FROM wa_contacts
                """
                df = pd.read_sql_query(query, self.wa_conn)
                
                # msgstore'dan LID -> normal JID eşleştirmesini al
                try:
                    lid_map_query = """
                    SELECT 
                        lid.raw_string as lid_jid,
                        jid.raw_string as normal_jid
                    FROM jid_map jm
                    JOIN jid lid ON jm.lid_row_id = lid._id
                    JOIN jid jid ON jm.jid_row_id = jid._id
                    """
                    lid_map = pd.read_sql_query(lid_map_query, self.msgstore_conn)
                    
                    # LID map'i kaydet (analyzer için)
                    self.lid_map_df = lid_map
                    
                    # LID -> isim eşleştirmesi oluştur
                    lid_to_normal = dict(zip(lid_map['lid_jid'], lid_map['normal_jid']))
                    
                    # Her LID için wa_contacts'tan ismi bul
                    lid_contacts = []
                    for lid_jid, normal_jid in lid_to_normal.items():
                        contact = df[df['jid'] == normal_jid]
                        if not contact.empty:
                            lid_contacts.append({
                                'jid': lid_jid,
                                'display_name': contact.iloc[0]['display_name'],
                                'given_name': contact.iloc[0]['given_name'],
                                'status': contact.iloc[0]['status']
                            })
                    
                    # LID kişilerini ekle
                    if lid_contacts:
                        lid_df = pd.DataFrame(lid_contacts)
                        df = pd.concat([df, lid_df], ignore_index=True)
                    
                    print(f"✅ {len(df)} kişi yüklendi (LID eşleştirme ile)")
                except Exception as lid_error:
                    print(f"   ⚠️ LID eşleştirme yapılamadı: {lid_error}")
                    print(f"✅ {len(df)} kişi yüklendi")
                    self.lid_map_df = pd.DataFrame()
                
                return df
            else:
                # msgstore'dan jid tablosunu kullan
                query = """
                SELECT 
                    j._id as jid_row_id,
                    j.raw_string as jid,
                    j.user as display_name
                FROM jid AS j
                WHERE j.type IN (0, 1)
                """
                df = pd.read_sql_query(query, self.msgstore_conn)
                
                # LID map'i al (wa.db olmasa da)
                try:
                    lid_map_query = """
                    SELECT 
                        lid.raw_string as lid_jid,
                        jid.raw_string as normal_jid
                    FROM jid_map jm
                    JOIN jid lid ON jm.lid_row_id = lid._id
                    JOIN jid jid ON jm.jid_row_id = jid._id
                    """
                    self.lid_map_df = pd.read_sql_query(lid_map_query, self.msgstore_conn)
                except:
                    self.lid_map_df = pd.DataFrame()
                
                print(f"✅ {len(df)} JID kaydı yüklendi (wa.db yok)")
                return df
                
        except Exception as e:
            print(f"⚠️ Kişi okuma hatası: {e}")
            return pd.DataFrame()
    
    def get_groups(self):
        """Grup bilgilerini çek"""
        try:
            # msgstore'dan chat tablosundan grupları al
            query = """
            SELECT 
                c._id as chat_row_id,
                j.raw_string as group_id,
                c.subject as group_name,
                c.created_timestamp
            FROM chat AS c
            JOIN jid AS j ON c.jid_row_id = j._id
            WHERE j.raw_string LIKE '%@g.us'
            """
            df = pd.read_sql_query(query, self.msgstore_conn)
            
            # Grup adı yoksa JID'den oluştur
            if 'group_name' in df.columns:
                df['group_name'] = df['group_name'].fillna(
                    df['group_id'].str.split('@').str[0]
                )
            else:
                df['group_name'] = df['group_id'].str.split('@').str[0]
            
            print(f"✅ {len(df)} grup bulundu")
            return df
                
        except Exception as e:
            print(f"⚠️ Grup okuma hatası: {e}")
            return pd.DataFrame()
    
    def get_group_participants(self):
        """Grup üyelerini çek"""
        try:
            if self.wa_conn:
                query = """
                SELECT 
                    gjid as group_id,
                    jid as participant_jid,
                    admin as is_admin
                FROM group_participants
                """
                df = pd.read_sql_query(query, self.wa_conn)
                print(f"✅ {len(df)} grup üyesi kaydı yüklendi")
                return df
            else:
                print("⚠️ wa.db yok, grup üyeleri belirlenemiyor")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"⚠️ Grup üyesi okuma hatası: {e}")
            return pd.DataFrame()
    
    def get_media_info(self):
        """Medya dosya bilgilerini çek"""
        try:
            # message_media tablosundan medya bilgilerini al
            query = """
            SELECT 
                m._id as message_id,
                m.message_type as media_type,
                mm.file_size as media_size,
                mm.media_name,
                mm.mime_type as media_mime_type,
                m.timestamp
            FROM message AS m
            LEFT JOIN message_media AS mm ON m._id = mm.message_row_id
            WHERE m.message_type > 0
            """
            df = pd.read_sql_query(query, self.msgstore_conn)
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
            print(f"✅ {len(df)} medya kaydı yüklendi")
            return df
            
        except Exception as e:
            print(f"⚠️ Medya okuma hatası: {e}")
            # Alternatif: sadece message tablosundan
            try:
                query = """
                SELECT 
                    _id as message_id,
                    message_type as media_type,
                    timestamp
                FROM message
                WHERE message_type > 0
                """
                df = pd.read_sql_query(query, self.msgstore_conn)
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
                print(f"✅ {len(df)} medya kaydı yüklendi (temel)")
                return df
            except:
                return pd.DataFrame()
    
    def get_table_info(self):
        """Veritabanı tablo yapısını göster (debug için)"""
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            tables = pd.read_sql_query(query, self.msgstore_conn)
            print("\n📋 msgstore.db Tabloları:")
            print(tables)
            
            if self.wa_conn:
                tables_wa = pd.read_sql_query(query, self.wa_conn)
                print("\n📋 wa.db Tabloları:")
                print(tables_wa)
                
        except Exception as e:
            print(f"❌ Tablo bilgisi alınamadı: {e}")


def test_reader():
    """Test fonksiyonu"""
    print("=== WhatsApp Veritabanı Okuyucu Test ===")
    
    # Test için örnek yollar
    msgstore = "msgstore.db"
    wa_db = "wa.db"
    
    if not os.path.exists(msgstore):
        print("⚠️ Test için msgstore.db dosyası bulunamadı")
        print("Kullanım: reader = WhatsAppDatabaseReader('msgstore.db', 'wa.db')")
        return
    
    reader = WhatsAppDatabaseReader(msgstore, wa_db)
    reader.connect()
    
    # Tablo yapısını göster
    reader.get_table_info()
    
    # Verileri çek
    messages = reader.get_messages()
    contacts = reader.get_contacts()
    groups = reader.get_groups()
    media = reader.get_media_info()
    
    print(f"\n📊 Özet:")
    print(f"  Mesajlar: {len(messages)}")
    print(f"  Kişiler: {len(contacts)}")
    print(f"  Gruplar: {len(groups)}")
    print(f"  Medya: {len(media)}")
    
    reader.close()


if __name__ == "__main__":
    test_reader()

