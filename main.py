#!/usr/bin/env python3
"""
WhatsApp Database Analyzer
Analyzes msgstore.db and wa.db files and generates detailed HTML reports
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
    """Main application class"""
    
    def __init__(self, msgstore_path, wa_db_path=None, output_file='report.html'):
        """
        Args:
            msgstore_path: msgstore.db dosya yolu
            wa_db_path: wa.db dosya yolu (opsiyonel)
            output_file: Output HTML filename
        """
        self.msgstore_path = msgstore_path
        self.wa_db_path = wa_db_path
        self.output_file = output_file
        
        self.reader = None
        self.analyzer = None
        self.report_generator = None
    
    def validate_files(self):
        """Check file existence"""
        if not os.path.exists(self.msgstore_path):
            print(f"❌ Error: msgstore.db file not found: {self.msgstore_path}")
            return False
        
        if self.wa_db_path and not os.path.exists(self.wa_db_path):
            print(f"⚠️ Warning: wa.db file not found: {self.wa_db_path}")
            print("   Group analysis will be limited, continuing...")
            self.wa_db_path = None
        
        return True
    
    def run(self):
        """Main execution function"""
        print("=" * 70)
        print("📱 WhatsApp Database Analyzer")
        print("=" * 70)
        print()
        
        # Check files
        if not self.validate_files():
            return False
        
        try:
            # 1. Read database
            print("📖 1/4 - Reading database...")
            print("-" * 70)
            self.reader = WhatsAppDatabaseReader(self.msgstore_path, self.wa_db_path)
            self.reader.connect()
            
            messages_df = self.reader.get_messages()
            contacts_df = self.reader.get_contacts()
            groups_df = self.reader.get_groups()
            media_df = self.reader.get_media_info()
            
            if messages_df.empty:
                print("❌ Error: Message data could not be read!")
                return False
            
            print(f"   ✅ {len(messages_df):,} messages loaded")
            print(f"   ✅ {len(contacts_df):,} contacts loaded")
            print(f"   ✅ {len(groups_df):,} groups loaded")
            print()
            
            # 2. Analiz yap
            print("🔍 2/4 - Analyzing data...")
            print("-" * 70)
            
            # Get LID map (if available)
            lid_map_df = getattr(self.reader, 'lid_map_df', None)
            
            self.analyzer = WhatsAppAnalyzer(
                messages_df, 
                contacts_df, 
                groups_df, 
                media_df,
                lid_map_df
            )
            
            # Show quick statistics
            stats = self.analyzer.get_general_statistics()
            print(f"   📊 Total messages: {stats.get('total_messages', 0):,}")
            print(f"   💬 Total chats: {stats.get('total_chats', 0):,}")
            print(f"   👥 Total groups: {stats.get('total_groups', 0):,}")
            print(f"   🎬 Total media: {stats.get('total_media', 0):,}")
            print(f"   📅 Date range: {stats.get('first_message_date', 'N/A')} → {stats.get('last_message_date', 'N/A')}")
            print()
            
            # 3. Generate report
            print("📝 3/4 - Generating HTML report...")
            print("-" * 70)
            self.report_generator = ReportGenerator(self.analyzer, self.output_file)
            output_path = self.report_generator.generate_html_report()
            print()
            
            # 4. Completed
            print("✅ 4/4 - Process completed!")
            print("=" * 70)
            print()
            print(f"🎉 Report successfully created!")
            print(f"📄 File: {os.path.abspath(output_path)}")
            print(f"📊 File size: {os.path.getsize(output_path) / 1024:.2f} KB")
            print()
            print("💡 Open the report in your browser:")
            print(f"   file://{os.path.abspath(output_path)}")
            print()
            
            # Close database connection
            self.reader.close()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Process cancelled by user")
            return False
        
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            if self.reader:
                self.reader.close()


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='WhatsApp Database Analyzer - Generates detailed HTML reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  %(prog)s msgstore.db
  %(prog)s msgstore.db -w wa.db
  %(prog)s msgstore.db -w wa.db -o my_report.html
  %(prog)s /path/to/msgstore.db -w /path/to/wa.db

Notlar:
  - msgstore.db: Required, message database
  - wa.db: Optional, for contact and group information (recommended)
  - Report is generated as 'report.html' by default
  - All operations are offline, your data is private
        """
    )
    
    parser.add_argument(
        'msgstore',
        help='msgstore.db dosya yolu (zorunlu)'
    )
    
    parser.add_argument(
        '-w', '--wa-db',
        dest='wa_db',
        help='wa.db file path (optional, for group and contact analysis)',
        default=None
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output',
        help='Output HTML filename (default: report.html)',
        default='report.html'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n" + "=" * 70)
        print("Quick Start:")
        print("=" * 70)
        print("1. Copy your WhatsApp database files to this folder:")
        print("   - msgstore.db (required)")
        print("   - wa.db (recommended)")
        print()
        print("2. Run the program:")
        print("   python main.py msgstore.db -w wa.db")
        print()
        print("3. Open the generated report.html in your browser")
        print("=" * 70)
        sys.exit(0)
    
    args = parser.parse_args()
    
    # Run application
    app = WhatsAppAnalyzerApp(
        msgstore_path=args.msgstore,
        wa_db_path=args.wa_db,
        output_file=args.output
    )
    
    success = app.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

