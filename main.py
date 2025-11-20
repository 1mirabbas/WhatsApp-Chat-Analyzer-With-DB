#!/usr/bin/env python3
"""
WhatsApp Veritabanı Analiz Aracı
msgstore.db ve wa.db dosyalarını analiz ederek detaylı HTML raporu oluşturur
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

from database_reader import WhatsAppDatabaseReader
from analyzer import WhatsAppAnalyzer
from report_generator import ReportGenerator


class WhatsAppAnalyzerApp:
    """Ana uygulama sınıfı"""
    
    def __init__(self, msgstore_path, wa_db_path=None, output_file='report.html'):
        """
        Args:
            msgstore_path: msgstore.db dosya yolu
            wa_db_path: wa.db dosya yolu (opsiyonel)
            output_file: Çıktı HTML dosya adı
        """
        self.msgstore_path = msgstore_path
        self.wa_db_path = wa_db_path
        self.output_file = output_file
        
        self.reader = None
        self.analyzer = None
        self.report_generator = None
    
    def validate_files(self):
        """Dosya varlığını kontrol et"""
        if not os.path.exists(self.msgstore_path):
            print(f"❌ Hata: msgstore.db dosyası bulunamadı: {self.msgstore_path}")
            return False
        
        if self.wa_db_path and not os.path.exists(self.wa_db_path):
            print(f"⚠️ Uyarı: wa.db dosyası bulunamadı: {self.wa_db_path}")
            print("   Grup analizi sınırlı olacak, devam ediliyor...")
            self.wa_db_path = None
        
        return True
    
    def run(self):
        """Ana çalıştırma fonksiyonu"""
        print("=" * 70)
        print("📱 WhatsApp Veritabanı Analiz Aracı")
        print("=" * 70)
        print()
        
        # Dosyaları kontrol et
        if not self.validate_files():
            return False
        
        try:
            # 1. Veritabanını oku
            print("📖 1/4 - Veritabanı okunuyor...")
            print("-" * 70)
            self.reader = WhatsAppDatabaseReader(self.msgstore_path, self.wa_db_path)
            self.reader.connect()
            
            messages_df = self.reader.get_messages()
            contacts_df = self.reader.get_contacts()
            groups_df = self.reader.get_groups()
            media_df = self.reader.get_media_info()
            
            if messages_df.empty:
                print("❌ Hata: Mesaj verisi okunamadı!")
                return False
            
            print(f"   ✅ {len(messages_df):,} mesaj yüklendi")
            print(f"   ✅ {len(contacts_df):,} kişi bilgisi yüklendi")
            print(f"   ✅ {len(groups_df):,} grup bilgisi yüklendi")
            print()
            
            # 2. Analiz yap
            print("🔍 2/4 - Veriler analiz ediliyor...")
            print("-" * 70)
            
            # LID map'i al (eğer varsa)
            lid_map_df = getattr(self.reader, 'lid_map_df', None)
            
            self.analyzer = WhatsAppAnalyzer(
                messages_df, 
                contacts_df, 
                groups_df, 
                media_df,
                lid_map_df
            )
            
            # Hızlı istatistik göster
            stats = self.analyzer.get_general_statistics()
            print(f"   📊 Toplam mesaj: {stats.get('total_messages', 0):,}")
            print(f"   💬 Toplam sohbet: {stats.get('total_chats', 0):,}")
            print(f"   👥 Toplam grup: {stats.get('total_groups', 0):,}")
            print(f"   🎬 Toplam medya: {stats.get('total_media', 0):,}")
            print(f"   📅 Tarih aralığı: {stats.get('first_message_date', 'N/A')} → {stats.get('last_message_date', 'N/A')}")
            print()
            
            # 3. Rapor oluştur
            print("📝 3/4 - HTML raporu oluşturuluyor...")
            print("-" * 70)
            self.report_generator = ReportGenerator(self.analyzer, self.output_file)
            output_path = self.report_generator.generate_html_report()
            print()
            
            # 4. Tamamlandı
            print("✅ 4/4 - İşlem tamamlandı!")
            print("=" * 70)
            print()
            print(f"🎉 Rapor başarıyla oluşturuldu!")
            print(f"📄 Dosya: {os.path.abspath(output_path)}")
            print(f"📊 Dosya boyutu: {os.path.getsize(output_path) / 1024:.2f} KB")
            print()
            print("💡 Raporu görüntülemek için tarayıcınızda açın:")
            print(f"   file://{os.path.abspath(output_path)}")
            print()
            
            # Veritabanı bağlantısını kapat
            self.reader.close()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️ İşlem kullanıcı tarafından iptal edildi")
            return False
            
        except Exception as e:
            print(f"\n❌ Hata oluştu: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            if self.reader:
                self.reader.close()


def main():
    """Komut satırı arayüzü"""
    parser = argparse.ArgumentParser(
        description='WhatsApp Veritabanı Analiz Aracı - Detaylı HTML raporu oluşturur',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Kullanım Örnekleri:
  %(prog)s msgstore.db
  %(prog)s msgstore.db -w wa.db
  %(prog)s msgstore.db -w wa.db -o my_report.html
  %(prog)s /path/to/msgstore.db -w /path/to/wa.db

Notlar:
  - msgstore.db: Zorunlu, mesaj veritabanı
  - wa.db: Opsiyonel, kişi ve grup bilgileri için (önerilir)
  - Rapor varsayılan olarak 'report.html' adıyla oluşturulur
  - Tüm işlemler offline yapılır, verileriniz gizlidir
        """
    )
    
    parser.add_argument(
        'msgstore',
        help='msgstore.db dosya yolu (zorunlu)'
    )
    
    parser.add_argument(
        '-w', '--wa-db',
        dest='wa_db',
        help='wa.db dosya yolu (opsiyonel, grup ve kişi analizi için)',
        default=None
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output',
        help='Çıktı HTML dosya adı (varsayılan: report.html)',
        default='report.html'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    # Eğer argüman verilmemişse yardım göster
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n" + "=" * 70)
        print("Hızlı Başlangıç:")
        print("=" * 70)
        print("1. WhatsApp veritabanı dosyalarınızı bu klasöre kopyalayın:")
        print("   - msgstore.db (zorunlu)")
        print("   - wa.db (önerilir)")
        print()
        print("2. Programı çalıştırın:")
        print("   python main.py msgstore.db -w wa.db")
        print()
        print("3. Oluşan report.html dosyasını tarayıcınızda açın")
        print("=" * 70)
        sys.exit(0)
    
    args = parser.parse_args()
    
    # Uygulamayı çalıştır
    app = WhatsAppAnalyzerApp(
        msgstore_path=args.msgstore,
        wa_db_path=args.wa_db,
        output_file=args.output
    )
    
    success = app.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

