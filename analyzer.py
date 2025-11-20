"""
WhatsApp Mesaj Analiz Modülü
Tüm istatistik ve analiz işlemlerini yapar
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import re
import emoji as emoji_lib


class WhatsAppAnalyzer:
    """WhatsApp mesajlarını analiz eden sınıf"""
    
    def __init__(self, messages_df, contacts_df=None, groups_df=None, media_df=None, lid_map_df=None):
        """
        Args:
            messages_df: Mesajlar DataFrame
            contacts_df: Kişiler DataFrame (opsiyonel)
            groups_df: Gruplar DataFrame (opsiyonel)
            media_df: Medya DataFrame (opsiyonel)
            lid_map_df: LID eşleştirme DataFrame (opsiyonel)
        """
        self.messages = messages_df.copy()
        self.contacts = contacts_df if contacts_df is not None else pd.DataFrame()
        self.groups = groups_df if groups_df is not None else pd.DataFrame()
        self.media = media_df if media_df is not None else pd.DataFrame()
        self.lid_map = lid_map_df if lid_map_df is not None else pd.DataFrame()
        
        # Tarih sütunlarını ekle
        if 'datetime' in self.messages.columns:
            self.messages['date'] = self.messages['datetime'].dt.date
            self.messages['year'] = self.messages['datetime'].dt.year
            self.messages['month'] = self.messages['datetime'].dt.month
            self.messages['day'] = self.messages['datetime'].dt.day
            self.messages['hour'] = self.messages['datetime'].dt.hour
            self.messages['day_of_week'] = self.messages['datetime'].dt.dayofweek
            self.messages['day_name'] = self.messages['datetime'].dt.day_name()
    
    def get_contact_name(self, chat_id):
        """Chat ID'den kişi adını bul"""
        if pd.isna(chat_id) or chat_id is None:
            return "Bilinmeyen"
        
        chat_id = str(chat_id)
        original_chat_id = chat_id
        
        # Eğer LID ise, önce normal JID'ye çevir
        if '@lid' in chat_id and not self.lid_map.empty:
            if 'lid_jid' in self.lid_map.columns and 'normal_jid' in self.lid_map.columns:
                lid_row = self.lid_map[self.lid_map['lid_jid'] == chat_id]
                if not lid_row.empty:
                    chat_id = lid_row.iloc[0]['normal_jid']
        
        # Kişi adını ara
        if not self.contacts.empty and 'jid' in self.contacts.columns:
            contact = self.contacts[self.contacts['jid'] == chat_id]
            if not contact.empty:
                if 'display_name' in contact.columns and pd.notna(contact.iloc[0]['display_name']):
                    name = str(contact.iloc[0]['display_name'])
                    if name and name != 'None' and name.strip():
                        return name
                elif 'given_name' in contact.columns and pd.notna(contact.iloc[0]['given_name']):
                    name = str(contact.iloc[0]['given_name'])
                    if name and name != 'None' and name.strip():
                        return name
        
        # İsim bulunamadı, telefon numarasını göster
        if '@s.whatsapp.net' in chat_id:
            phone = chat_id.split('@')[0]
            # + ekle eğer yoksa
            if not phone.startswith('+'):
                phone = '+' + phone
            return phone
        elif '@lid' in original_chat_id:
            # LID'den telefon numarasına çevirebildiysek onu göster
            if chat_id != original_chat_id and '@s.whatsapp.net' in chat_id:
                phone = chat_id.split('@')[0]
                if not phone.startswith('+'):
                    phone = '+' + phone
                return phone
            # Çeviremediyse LID'yi göster
            return original_chat_id.split('@')[0]
        elif '@' in chat_id:
            return chat_id.split('@')[0]
        
        return chat_id
    
    def get_general_statistics(self):
        """Genel istatistikleri hesapla"""
        stats = {}
        
        # Temel sayılar
        stats['total_messages'] = len(self.messages)
        stats['total_chats'] = self.messages['chat_id'].nunique()
        stats['total_media'] = len(self.messages[self.messages['media_type'].notna() & (self.messages['media_type'] > 0)])
        
        # Grup vs kişisel
        if 'is_group' in self.messages.columns:
            stats['total_groups'] = len(self.messages[self.messages['is_group'] == True]['chat_id'].unique())
            stats['total_personal_chats'] = stats['total_chats'] - stats['total_groups']
        else:
            stats['total_groups'] = 0
            stats['total_personal_chats'] = stats['total_chats']
        
        # Tarih bilgileri
        if 'datetime' in self.messages.columns:
            valid_dates = self.messages['datetime'].dropna()
            if not valid_dates.empty:
                stats['first_message_date'] = valid_dates.min().strftime('%Y-%m-%d %H:%M:%S')
                stats['last_message_date'] = valid_dates.max().strftime('%Y-%m-%d %H:%M:%S')
                stats['date_range_days'] = (valid_dates.max() - valid_dates.min()).days
            else:
                stats['first_message_date'] = "Bilinmiyor"
                stats['last_message_date'] = "Bilinmiyor"
                stats['date_range_days'] = 0
        
        # En aktif gün
        if 'date' in self.messages.columns:
            most_active_day = self.messages.groupby('date').size().idxmax()
            stats['most_active_day'] = str(most_active_day)
            stats['most_active_day_count'] = int(self.messages.groupby('date').size().max())
        
        # Gönderilen vs alınan
        if 'from_me' in self.messages.columns:
            stats['sent_messages'] = int((self.messages['from_me'] == 1).sum())
            stats['received_messages'] = int((self.messages['from_me'] == 0).sum())
        
        return stats
    
    def get_message_type_distribution(self):
        """Mesaj türü dağılımı"""
        distribution = {
            'Text': 0,
            'Image': 0,
            'Video': 0,
            'Audio': 0,
            'Document': 0,
            'Sticker': 0,
            'Location': 0,
            'Contact': 0,
            'GIF': 0,
            'Other': 0
        }
        
        if 'media_type' not in self.messages.columns:
            distribution['Text'] = len(self.messages)
            return distribution
        
        # WhatsApp media_type kodları:
        # 0 or NULL = Text
        # 1 = Image
        # 2 = Audio
        # 3 = Video
        # 4 = Contact Card
        # 5 = Location
        # 13 = GIF
        # 20 = Sticker
        # 9 = Document
        
        for _, row in self.messages.iterrows():
            media_type = row.get('media_type')
            
            if pd.isna(media_type) or media_type == 0:
                distribution['Text'] += 1
            elif media_type == 1:
                distribution['Image'] += 1
            elif media_type == 2:
                distribution['Audio'] += 1
            elif media_type == 3:
                distribution['Video'] += 1
            elif media_type == 4:
                distribution['Contact'] += 1
            elif media_type == 5:
                distribution['Location'] += 1
            elif media_type == 13:
                distribution['GIF'] += 1
            elif media_type == 20:
                distribution['Sticker'] += 1
            elif media_type == 9:
                distribution['Document'] += 1
            else:
                distribution['Other'] += 1
        
        return distribution
    
    def get_messages_by_month(self):
        """Aylara göre mesaj sayısı"""
        if 'datetime' not in self.messages.columns:
            return pd.DataFrame()
        
        monthly = self.messages.groupby(self.messages['datetime'].dt.to_period('M')).size()
        monthly_df = pd.DataFrame({
            'month': monthly.index.astype(str),
            'count': monthly.values
        })
        return monthly_df
    
    def get_messages_by_day_of_week(self):
        """Haftanın günlerine göre mesaj dağılımı"""
        if 'day_of_week' not in self.messages.columns:
            return pd.DataFrame()
        
        day_names = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        daily = self.messages.groupby('day_of_week').size()
        
        daily_df = pd.DataFrame({
            'day_name': [day_names[int(i)] if i < len(day_names) else str(i) for i in daily.index],
            'count': daily.values
        })
        return daily_df
    
    def get_messages_by_hour(self):
        """Saatlere göre mesaj dağılımı"""
        if 'hour' not in self.messages.columns:
            return pd.DataFrame()
        
        hourly = self.messages.groupby('hour').size()
        hourly_df = pd.DataFrame({
            'hour': hourly.index,
            'count': hourly.values
        })
        return hourly_df
    
    def get_top_contacts(self, limit=20):
        """En çok mesajlaşılan kişiler"""
        if 'is_group' in self.messages.columns:
            personal_messages = self.messages[self.messages['is_group'] == False]
        else:
            personal_messages = self.messages
        
        contact_stats = personal_messages.groupby('chat_id').agg({
            'message_id': 'count',
            'from_me': lambda x: (x == 1).sum(),
            'datetime': 'max'
        }).reset_index()
        
        contact_stats.columns = ['chat_id', 'total_messages', 'sent_by_me', 'last_message']
        contact_stats['received'] = contact_stats['total_messages'] - contact_stats['sent_by_me']
        
        # Kişi isimlerini ekle
        contact_stats['contact_name'] = contact_stats['chat_id'].apply(self.get_contact_name)
        
        # Balance score hesapla
        contact_stats['balance_score'] = (
            contact_stats['sent_by_me'] / (contact_stats['total_messages'] + 1)
        ).round(2)
        
        contact_stats = contact_stats.sort_values('total_messages', ascending=False).head(limit)
        return contact_stats
    
    def get_group_statistics(self):
        """Grup istatistikleri"""
        if 'is_group' not in self.messages.columns:
            return pd.DataFrame()
        
        group_messages = self.messages[self.messages['is_group'] == True]
        
        if group_messages.empty:
            return pd.DataFrame()
        
        group_stats = group_messages.groupby('chat_id').agg({
            'message_id': 'count',
            'datetime': ['min', 'max']
        }).reset_index()
        
        group_stats.columns = ['group_id', 'total_messages', 'first_message', 'last_message']
        
        # Grup isimlerini ekle
        group_stats['group_name'] = group_stats['group_id'].apply(
            lambda x: x.split('@')[0] if '@' in x else x
        )
        
        group_stats = group_stats.sort_values('total_messages', ascending=False)
        return group_stats
    
    def get_media_statistics(self):
        """Medya istatistikleri"""
        media_stats = {}
        
        distribution = self.get_message_type_distribution()
        media_stats['total_images'] = distribution['Image']
        media_stats['total_videos'] = distribution['Video']
        media_stats['total_audio'] = distribution['Audio']
        media_stats['total_documents'] = distribution['Document']
        media_stats['total_gifs'] = distribution['GIF']
        media_stats['total_stickers'] = distribution['Sticker']
        
        return media_stats
    
    def get_top_media_senders(self, limit=10):
        """En çok medya gönderenler"""
        media_messages = self.messages[self.messages['media_type'].notna() & (self.messages['media_type'] > 0)]
        
        if media_messages.empty:
            return pd.DataFrame()
        
        # Kişi bazında toplam medya sayısı
        media_by_contact = media_messages.groupby('chat_id').agg({
            'message_id': 'count'
        }).reset_index()
        
        media_by_contact.columns = ['chat_id', 'total_media']
        media_by_contact = media_by_contact.sort_values('total_media', ascending=False).head(limit)
        
        # Kişi isimlerini ekle
        media_by_contact['contact_name'] = media_by_contact['chat_id'].apply(self.get_contact_name)
        
        # Medya türlerine göre detay
        for media_type in [1, 2, 3]:  # Image, Audio, Video
            type_counts = media_messages[media_messages['media_type'] == media_type].groupby('chat_id').size()
            type_name = {1: 'images', 2: 'audio', 3: 'videos'}.get(media_type, f'type_{media_type}')
            media_by_contact[type_name] = media_by_contact['chat_id'].map(type_counts).fillna(0).astype(int)
        
        return media_by_contact
    
    def extract_text_content(self):
        """Metin içeriklerini çıkar"""
        if 'message_text' not in self.messages.columns:
            return []
        
        texts = self.messages['message_text'].dropna()
        # Byte string olanları çöz
        texts = texts.apply(lambda x: x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else str(x))
        return texts.tolist()
    
    def get_word_frequency(self, limit=50):
        """En çok kullanılan kelimeler"""
        texts = self.extract_text_content()
        
        # Tüm metinleri birleştir
        all_text = ' '.join(texts)
        
        # Kelimelere ayır (Türkçe karakterleri koru)
        words = re.findall(r'\b[\wğüşıöçĞÜŞİÖÇ]+\b', all_text.lower())
        
        # Kısa kelimeleri filtrele
        words = [w for w in words if len(w) > 2]
        
        # Stop words (yaygın kelimeler) - Türkçe
        stop_words = {'bir', 'bu', 'şu', 've', 'veya', 'ama', 'fakat', 'için', 'ile', 'mi', 'mu', 
                      'mı', 'mü', 'da', 'de', 'ta', 'te', 'ki', 'ne', 'var', 'yok', 'ben', 'sen',
                      'o', 'biz', 'siz', 'onlar', 'the', 'a', 'an', 'and', 'or', 'but', 'is', 
                      'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 
                      'did', 'will', 'would', 'could', 'should'}
        
        words = [w for w in words if w not in stop_words]
        
        # Frekans hesapla
        word_freq = Counter(words).most_common(limit)
        
        return pd.DataFrame(word_freq, columns=['word', 'frequency'])
    
    def get_emoji_statistics(self, limit=30):
        """Emoji istatistikleri"""
        texts = self.extract_text_content()
        all_text = ' '.join(texts)
        
        # Emojileri çıkar
        emojis = [c for c in all_text if c in emoji_lib.EMOJI_DATA]
        
        if not emojis:
            return pd.DataFrame()
        
        emoji_freq = Counter(emojis).most_common(limit)
        return pd.DataFrame(emoji_freq, columns=['emoji', 'frequency'])
    
    def get_message_length_stats(self):
        """Mesaj uzunluk istatistikleri"""
        texts = self.extract_text_content()
        lengths = [len(text) for text in texts]
        
        if not lengths:
            return {}
        
        stats = {
            'average_length': np.mean(lengths),
            'median_length': np.median(lengths),
            'max_length': max(lengths),
            'min_length': min(lengths)
        }
        
        return stats
    
    def get_activity_heatmap_data(self):
        """Aktivite ısı haritası için veri (gün x saat)"""
        if 'day_of_week' not in self.messages.columns or 'hour' not in self.messages.columns:
            return pd.DataFrame()
        
        heatmap = self.messages.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
        
        day_names = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        heatmap.index = [day_names[int(i)] if int(i) < len(day_names) else str(i) for i in heatmap.index]
        
        return heatmap
    
    def get_deleted_messages_count(self):
        """Silinmiş mesaj sayısı (eğer varsa)"""
        # WhatsApp'ta deleted message flag'i varsa
        if 'status' in self.messages.columns:
            deleted = self.messages[self.messages['status'] == 13]  # 13 = deleted
            return len(deleted)
        return 0
    
    def get_conversation_with_contact(self, chat_id, limit=100):
        """Belirli bir kişiyle olan konuşmayı getir"""
        if 'chat_id' not in self.messages.columns:
            return pd.DataFrame()
        
        conv = self.messages[self.messages['chat_id'] == chat_id].copy()
        
        if conv.empty:
            return pd.DataFrame()
        
        # Sadece gerekli sütunları al ve sırala
        conv = conv.sort_values('timestamp', ascending=True)
        
        # Limit uygula
        if len(conv) > limit:
            # Son N mesajı al
            conv = conv.tail(limit)
        
        return conv
    
    def get_longest_messages(self, limit=10):
        """En uzun mesajları getir"""
        texts = self.extract_text_content()
        
        if not texts:
            return pd.DataFrame()
        
        # Mesajları uzunluklarıyla birlikte sakla
        msg_lengths = []
        for idx, text in enumerate(texts):
            if pd.notna(text) and len(str(text)) > 10:  # Çok kısa olanları atla
                msg_lengths.append({
                    'index': idx,
                    'length': len(str(text)),
                    'text': str(text)[:500]  # İlk 500 karakter
                })
        
        if not msg_lengths:
            return pd.DataFrame()
        
        df = pd.DataFrame(msg_lengths)
        df = df.sort_values('length', ascending=False).head(limit)
        
        return df
    
    def get_random_message_samples(self, count=20):
        """Rastgele mesaj örnekleri"""
        if 'message_text' not in self.messages.columns:
            return pd.DataFrame()
        
        text_messages = self.messages[self.messages['message_text'].notna()].copy()
        
        if text_messages.empty:
            return pd.DataFrame()
        
        sample_size = min(count, len(text_messages))
        samples = text_messages.sample(n=sample_size)
        
        return samples[['chat_id', 'from_me', 'datetime', 'message_text']]
    
    def get_conversation_details_for_contact(self, chat_id):
        """Bir kişi için detaylı konuşma bilgileri"""
        if 'chat_id' not in self.messages.columns:
            return {}
        
        conv = self.messages[self.messages['chat_id'] == chat_id].copy()
        
        if conv.empty:
            return {}
        
        details = {
            'chat_id': chat_id,
            'contact_name': self.get_contact_name(chat_id),
            'total_messages': len(conv),
            'sent_by_me': int((conv['from_me'] == 1).sum()),
            'received': int((conv['from_me'] == 0).sum()),
            'first_message': conv['datetime'].min() if 'datetime' in conv.columns else None,
            'last_message': conv['datetime'].max() if 'datetime' in conv.columns else None,
            'avg_message_length': conv['message_text'].str.len().mean() if 'message_text' in conv.columns else 0,
        }
        
        # Medya sayıları
        if 'media_type' in conv.columns:
            details['media_count'] = int((conv['media_type'] > 0).sum())
        else:
            details['media_count'] = 0
        
        # En aktif saatler
        if 'hour' in conv.columns:
            details['most_active_hour'] = int(conv.groupby('hour').size().idxmax())
        
        return details
    
    def get_recent_messages(self, limit=50):
        """Her kullanıcıdan en son mesajı getir"""
        if 'datetime' not in self.messages.columns:
            return pd.DataFrame()
        
        # Her chat_id için en son mesajı al
        recent_per_contact = []
        for chat_id in self.messages['chat_id'].unique():
            if pd.isna(chat_id):
                continue
            chat_messages = self.messages[self.messages['chat_id'] == chat_id]
            if not chat_messages.empty:
                last_msg = chat_messages.sort_values('datetime', ascending=False).iloc[0]
                recent_per_contact.append(last_msg)
        
        if not recent_per_contact:
            return pd.DataFrame()
        
        # DataFrame oluştur ve tarihe göre sırala
        recent_df = pd.DataFrame(recent_per_contact)
        recent_df = recent_df.sort_values('datetime', ascending=False).head(limit)
        
        return recent_df[['chat_id', 'from_me', 'datetime', 'message_text', 'media_type']]
    
    def get_first_messages(self, limit=50):
        """Her kullanıcıdan ilk mesajı getir"""
        if 'datetime' not in self.messages.columns:
            return pd.DataFrame()
        
        # Her chat_id için ilk mesajı al
        first_per_contact = []
        for chat_id in self.messages['chat_id'].unique():
            if pd.isna(chat_id):
                continue
            chat_messages = self.messages[self.messages['chat_id'] == chat_id]
            if not chat_messages.empty:
                first_msg = chat_messages.sort_values('datetime', ascending=True).iloc[0]
                first_per_contact.append(first_msg)
        
        if not first_per_contact:
            return pd.DataFrame()
        
        # DataFrame oluştur ve tarihe göre sırala
        first_df = pd.DataFrame(first_per_contact)
        first_df = first_df.sort_values('datetime', ascending=True).head(limit)
        
        return first_df[['chat_id', 'from_me', 'datetime', 'message_text', 'media_type']]
    
    def get_messages_by_keyword(self, keyword, limit=50):
        """Belirli bir kelime içeren mesajları bul"""
        if 'message_text' not in self.messages.columns:
            return pd.DataFrame()
        
        # Mesaj metinlerini string'e çevir
        self.messages['message_text_str'] = self.messages['message_text'].apply(
            lambda x: str(x).lower() if pd.notna(x) else ''
        )
        
        # Arama yap
        matches = self.messages[
            self.messages['message_text_str'].str.contains(keyword.lower(), na=False)
        ].copy()
        
        if matches.empty:
            return pd.DataFrame()
        
        return matches[['chat_id', 'from_me', 'datetime', 'message_text']].head(limit)
    
    def get_message_response_time_analysis(self):
        """Mesajlara yanıt verme süresini analiz et"""
        if 'datetime' not in self.messages.columns or 'from_me' not in self.messages.columns:
            return {}
        
        # Sohbetlere göre grupla
        response_times = []
        
        for chat_id in self.messages['chat_id'].unique():
            chat_msgs = self.messages[self.messages['chat_id'] == chat_id].sort_values('datetime')
            
            # Ardışık mesajlar arasında from_me değişimi var mı kontrol et
            for i in range(1, len(chat_msgs)):
                prev = chat_msgs.iloc[i-1]
                curr = chat_msgs.iloc[i]
                
                # Eğer karşı taraf mesaj attı ve ben cevapladıysam
                if prev['from_me'] == 0 and curr['from_me'] == 1:
                    time_diff = (curr['datetime'] - prev['datetime']).total_seconds() / 60  # dakika
                    if 0 < time_diff < 1440:  # 24 saat içinde
                        response_times.append(time_diff)
        
        if not response_times:
            return {}
        
        return {
            'avg_response_time_minutes': np.mean(response_times),
            'median_response_time_minutes': np.median(response_times),
            'min_response_time_minutes': np.min(response_times),
            'max_response_time_minutes': np.max(response_times),
        }


def test_analyzer():
    """Test fonksiyonu"""
    print("=== WhatsApp Analiz Modülü Test ===")
    
    # Örnek veri oluştur
    sample_data = {
        'message_id': range(100),
        'chat_id': ['user1@s.whatsapp.net'] * 50 + ['user2@s.whatsapp.net'] * 30 + ['group1@g.us'] * 20,
        'from_me': [0, 1] * 50,
        'timestamp': [1609459200000 + i * 86400000 for i in range(100)],
        'message_text': ['Test mesajı ' + str(i) for i in range(100)],
        'media_type': [0] * 70 + [1] * 15 + [3] * 15
    }
    
    df = pd.DataFrame(sample_data)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['is_group'] = df['chat_id'].str.contains('@g.us')
    
    analyzer = WhatsAppAnalyzer(df)
    
    print("\n📊 Genel İstatistikler:")
    stats = analyzer.get_general_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n📱 Mesaj Türü Dağılımı:")
    dist = analyzer.get_message_type_distribution()
    for key, value in dist.items():
        if value > 0:
            print(f"  {key}: {value}")
    
    print("\n👥 En Çok Mesajlaşılan Kişiler:")
    top = analyzer.get_top_contacts(5)
    print(top)


if __name__ == "__main__":
    test_analyzer()

