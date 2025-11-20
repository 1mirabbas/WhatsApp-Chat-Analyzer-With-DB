"""
WhatsApp HTML Rapor Oluşturma Modülü
Tüm analizleri görselleştirip tek bir HTML dosyasına aktarır
"""

import base64
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI olmadan çalışması için
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from wordcloud import WordCloud
import pandas as pd
import numpy as np
import json

# pandas için kısayol
pd.notna = pd.notna


class ReportGenerator:
    """HTML raporu oluşturan sınıf"""
    
    def __init__(self, analyzer, output_file='report.html'):
        """
        Args:
            analyzer: WhatsAppAnalyzer nesnesi
            output_file: Çıktı HTML dosya adı
        """
        self.analyzer = analyzer
        self.output_file = output_file
        self.plots = []
        
        # Renk paleti
        self.colors = {
            'primary': '#25D366',  # WhatsApp yeşili
            'secondary': '#128C7E',
            'background': '#0a0a0a',
            'card': '#1a1a1a',
            'text': '#e0e0e0',
            'accent': '#34B7F1'
        }
    
    def matplotlib_to_base64(self, fig):
        """Matplotlib figürünü base64'e çevir"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight', 
                    facecolor='#1a1a1a', edgecolor='none')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        return f"data:image/png;base64,{img_base64}"
    
    def plotly_to_html(self, fig):
        """Plotly figürünü HTML'e çevir"""
        return fig.to_html(include_plotlyjs='cdn', div_id=f'plot_{len(self.plots)}')
    
    def create_message_type_pie_chart(self, distribution):
        """Message type distribution pie chart"""
        # Filter zeros
        filtered = {k: v for k, v in distribution.items() if v > 0}
        
        if not filtered:
            return None
        
        fig = go.Figure(data=[go.Pie(
            labels=list(filtered.keys()),
            values=list(filtered.values()),
            hole=0.3,
            marker=dict(colors=px.colors.qualitative.Set3)
        )])
        
        fig.update_layout(
            title="Message Type Distribution",
            paper_bgcolor='#1a1a1a',
            plot_bgcolor='#1a1a1a',
            font=dict(color='#e0e0e0', size=12),
            height=400
        )
        
        return self.plotly_to_html(fig)
    
    def create_monthly_line_chart(self, monthly_df):
        """Aylık mesaj grafiği"""
        if monthly_df.empty:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly_df['month'],
            y=monthly_df['count'],
            mode='lines+markers',
            line=dict(color='#25D366', width=3),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title="Aylara Göre Mesaj Aktivitesi",
            xaxis_title="Ay",
            yaxis_title="Mesaj Sayısı",
            paper_bgcolor='#1a1a1a',
            plot_bgcolor='#1a1a1a',
            font=dict(color='#e0e0e0'),
            height=400,
            hovermode='x unified'
        )
        
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333')
        
        return self.plotly_to_html(fig)
    
    def create_hourly_bar_chart(self, hourly_df):
        """Saatlik mesaj dağılımı bar chart"""
        if hourly_df.empty:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=hourly_df['hour'],
            y=hourly_df['count'],
            marker=dict(color='#34B7F1')
        ))
        
        fig.update_layout(
            title="Saatlere Göre Mesaj Yoğunluğu",
            xaxis_title="Saat",
            yaxis_title="Mesaj Sayısı",
            paper_bgcolor='#1a1a1a',
            plot_bgcolor='#1a1a1a',
            font=dict(color='#e0e0e0'),
            height=400
        )
        
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333')
        
        return self.plotly_to_html(fig)
    
    def create_day_of_week_chart(self, daily_df):
        """Haftanın günlerine göre mesaj dağılımı"""
        if daily_df.empty:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily_df['day_name'],
            y=daily_df['count'],
            marker=dict(color='#128C7E')
        ))
        
        fig.update_layout(
            title="Haftanın Günlerine Göre Mesaj Dağılımı",
            xaxis_title="Gün",
            yaxis_title="Mesaj Sayısı",
            paper_bgcolor='#1a1a1a',
            plot_bgcolor='#1a1a1a',
            font=dict(color='#e0e0e0'),
            height=400
        )
        
        return self.plotly_to_html(fig)
    
    def create_heatmap(self, heatmap_data):
        """Aktivite ısı haritası (gün x saat)"""
        if heatmap_data.empty:
            return None
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='Greens',
            hoverongaps=False
        ))
        
        fig.update_layout(
            title="Aktivite Isı Haritası (Gün × Saat)",
            xaxis_title="Saat",
            yaxis_title="Gün",
            paper_bgcolor='#1a1a1a',
            plot_bgcolor='#1a1a1a',
            font=dict(color='#e0e0e0'),
            height=500
        )
        
        return self.plotly_to_html(fig)
    
    def create_wordcloud(self, word_freq_df):
        """Create word cloud"""
        if word_freq_df.empty or len(word_freq_df) == 0:
            return None
        
        try:
            # Create word frequency dictionary
            word_dict = dict(zip(word_freq_df['word'], word_freq_df['frequency']))
            
            # WordCloud oluştur
            wordcloud = WordCloud(
                width=1200, 
                height=600,
                background_color='#1a1a1a',
                colormap='viridis',
                max_words=100,
                relative_scaling=0.5,
                min_font_size=10
            ).generate_from_frequencies(word_dict)
            
            # Matplotlib figürü oluştur
            fig, ax = plt.subplots(figsize=(12, 6), facecolor='#1a1a1a')
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            ax.set_facecolor('#1a1a1a')
            plt.tight_layout(pad=0)
            
            return self.matplotlib_to_base64(fig)
            
        except Exception as e:
            print(f"⚠️ Failed to create word cloud: {e}")
            return None
    
    def create_top_contacts_chart(self, top_contacts_df):
        """En çok mesajlaşılan kişiler grafiği"""
        if top_contacts_df.empty:
            return None
        
        top_10 = top_contacts_df.head(10)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Sent',
            x=top_10['contact_name'],
            y=top_10['sent_by_me'],
            marker=dict(color='#25D366')
        ))
        
        fig.add_trace(go.Bar(
            name='Received',
            x=top_10['contact_name'],
            y=top_10['received'],
            marker=dict(color='#34B7F1')
        ))
        
        fig.update_layout(
            title="Top Contacts (Sent vs Received)",
            xaxis_title="Contact",
            yaxis_title="Message Count",
            barmode='stack',
            paper_bgcolor='#1a1a1a',
            plot_bgcolor='#1a1a1a',
            font=dict(color='#e0e0e0'),
            height=500,
            xaxis_tickangle=-45
        )
        
        return self.plotly_to_html(fig)
    
    def generate_html_report(self):
        """Ana HTML raporu oluştur"""
        print("📝 HTML raporu oluşturuluyor...")
        
        # Analizleri çalıştır
        general_stats = self.analyzer.get_general_statistics()
        msg_distribution = self.analyzer.get_message_type_distribution()
        monthly_data = self.analyzer.get_messages_by_month()
        hourly_data = self.analyzer.get_messages_by_hour()
        daily_data = self.analyzer.get_messages_by_day_of_week()
        top_contacts = self.analyzer.get_top_contacts(20)
        group_stats = self.analyzer.get_group_statistics()
        media_stats = self.analyzer.get_media_statistics()
        top_media_senders = self.analyzer.get_top_media_senders(10)
        word_freq = self.analyzer.get_word_frequency(50)
        emoji_stats = self.analyzer.get_emoji_statistics(30)
        msg_length = self.analyzer.get_message_length_stats()
        heatmap_data = self.analyzer.get_activity_heatmap_data()
        deleted_count = self.analyzer.get_deleted_messages_count()
        
        # YENİ: Detaylı analizler
        longest_messages = self.analyzer.get_longest_messages(10)
        recent_messages = self.analyzer.get_recent_messages(30)
        first_messages = self.analyzer.get_first_messages(20)
        response_time_stats = self.analyzer.get_message_response_time_analysis()
        
        # Grafikleri oluştur
        print("📊 Grafikler oluşturuluyor...")
        pie_chart = self.create_message_type_pie_chart(msg_distribution)
        monthly_chart = self.create_monthly_line_chart(monthly_data)
        hourly_chart = self.create_hourly_bar_chart(hourly_data)
        daily_chart = self.create_day_of_week_chart(daily_data)
        heatmap_chart = self.create_heatmap(heatmap_data)
        contacts_chart = self.create_top_contacts_chart(top_contacts)
        wordcloud_img = self.create_wordcloud(word_freq)
        
        # HTML içeriği oluştur
        html_content = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Analiz Raporu</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            color: #e0e0e0;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            background: linear-gradient(135deg, #128C7E 0%, #25D366 100%);
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 40px;
            box-shadow: 0 10px 40px rgba(37, 211, 102, 0.3);
        }}
        
        header h1 {{
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: #1a1a1a;
            padding: 25px;
            border-radius: 15px;
            border-left: 5px solid #25D366;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(37, 211, 102, 0.2);
        }}
        
        .stat-card h3 {{
            color: #25D366;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #fff;
        }}
        
        .stat-card .label {{
            font-size: 0.9em;
            color: #888;
            margin-top: 5px;
        }}
        
        .section {{
            background: #1a1a1a;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        
        .section-title {{
            font-size: 2em;
            color: #25D366;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #25D366;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        table th {{
            background: #128C7E;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: bold;
        }}
        
        table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #333;
        }}
        
        table tr:hover {{
            background: #252525;
        }}
        
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #1a1a1a;
            border-radius: 10px;
        }}
        
        .wordcloud-container {{
            text-align: center;
            margin: 30px 0;
        }}
        
        .wordcloud-container img {{
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.5);
        }}
        
        .emoji-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .emoji-item {{
            background: #252525;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.2s;
        }}
        
        .emoji-item:hover {{
            transform: scale(1.1);
        }}
        
        .emoji-item .emoji {{
            font-size: 2.5em;
            margin-bottom: 5px;
        }}
        
        .emoji-item .count {{
            font-size: 0.9em;
            color: #25D366;
            font-weight: bold;
        }}
        
        /* WhatsApp Web Tarzı Konuşma Arayüzü */
        .whatsapp-container {{
            display: flex;
            height: 700px;
            background: #0a0a0a;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
            box-shadow: 0 5px 30px rgba(0,0,0,0.5);
        }}
        
        .contacts-sidebar {{
            width: 350px;
            background: #1a1a1a;
            border-right: 1px solid #333;
            overflow-y: auto;
        }}
        
        .contact-item {{
            padding: 15px 20px;
            border-bottom: 1px solid #252525;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .contact-item:hover {{
            background: #252525;
        }}
        
        .contact-item.active {{
            background: #128C7E;
        }}
        
        .contact-item .name {{
            font-weight: bold;
            color: #e0e0e0;
            margin-bottom: 5px;
        }}
        
        .contact-item .preview {{
            font-size: 0.85em;
            color: #888;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .contact-item .count {{
            font-size: 0.75em;
            color: #25D366;
        }}
        
        .chat-area {{
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #0d1418;
        }}
        
        .chat-header {{
            background: #1a1a1a;
            padding: 15px 20px;
            border-bottom: 1px solid #333;
        }}
        
        .chat-header .name {{
            font-size: 1.2em;
            font-weight: bold;
            color: #e0e0e0;
        }}
        
        .chat-header .info {{
            font-size: 0.85em;
            color: #888;
            margin-top: 5px;
        }}
        
        .chat-messages {{
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #0d1418;
        }}
        
        .chat-placeholder {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #888;
        }}
        
        .chat-placeholder .icon {{
            font-size: 5em;
            margin-bottom: 20px;
            opacity: 0.3;
        }}
        
        .message-bubble {{
            margin: 8px 0;
            display: flex;
            animation: fadeIn 0.3s;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .message-bubble.sent {{
            justify-content: flex-end;
        }}
        
        .message-bubble.received {{
            justify-content: flex-start;
        }}
        
        .message-content {{
            max-width: 65%;
            padding: 10px 15px;
            border-radius: 8px;
            position: relative;
        }}
        
        .message-bubble.sent .message-content {{
            background: #056162;
            color: white;
            border-radius: 8px 8px 0 8px;
        }}
        
        .message-bubble.received .message-content {{
            background: #1f2c33;
            color: #e0e0e0;
            border-radius: 8px 8px 8px 0;
        }}
        
        .message-text {{
            word-wrap: break-word;
            margin-bottom: 5px;
        }}
        
        .message-time {{
            font-size: 0.7em;
            color: #8696a0;
            text-align: right;
        }}
        
        .message-bubble.received .message-time {{
            color: #667781;
        }}
        
        .media-indicator {{
            display: inline-block;
            padding: 5px 10px;
            background: rgba(0,0,0,0.3);
            border-radius: 5px;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding: 30px;
            color: #888;
            font-size: 0.9em;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            background: #25D366;
            color: white;
            font-size: 0.85em;
            font-weight: bold;
            margin: 5px;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            header h1 {{
                font-size: 2em;
            }}
            
            .section {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📱 WhatsApp Analysis Report</h1>
            <p>Detailed Message and Activity Analysis</p>
            <p style="margin-top: 10px; font-size: 0.9em;">Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <!-- GENERAL STATISTICS -->
        <div class="section">
            <h2 class="section-title">📊 General Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Messages</h3>
                    <div class="value">{general_stats.get('total_messages', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Total Chats</h3>
                    <div class="value">{general_stats.get('total_chats', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Total Groups</h3>
                    <div class="value">{general_stats.get('total_groups', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Total Media</h3>
                    <div class="value">{general_stats.get('total_media', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Sent Messages</h3>
                    <div class="value">{general_stats.get('sent_messages', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Received Messages</h3>
                    <div class="value">{general_stats.get('received_messages', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>First Message</h3>
                    <div class="value" style="font-size: 1.2em;">{general_stats.get('first_message_date', 'N/A')}</div>
                </div>
                <div class="stat-card">
                    <h3>Last Message</h3>
                    <div class="value" style="font-size: 1.2em;">{general_stats.get('last_message_date', 'N/A')}</div>
                </div>
            </div>
            
            {f'<p><span class="badge">Most Active Day: {general_stats.get("most_active_day", "N/A")} ({general_stats.get("most_active_day_count", 0)} messages)</span></p>' if 'most_active_day' in general_stats else ''}
            {f'<p><span class="badge">Analysis Period: {general_stats.get("date_range_days", 0)} days</span></p>' if 'date_range_days' in general_stats else ''}
            {f'<p><span class="badge">Deleted Messages: {deleted_count}</span></p>' if deleted_count > 0 else ''}
        </div>
        
        <!-- MESSAGE TYPE DISTRIBUTION -->
        <div class="section">
            <h2 class="section-title">📝 Message Type Distribution</h2>
            <div class="chart-container">
                {pie_chart if pie_chart else '<p>Grafik oluşturulamadı</p>'}
            </div>
            <div class="stats-grid" style="margin-top: 20px;">
                {''.join([f'<div class="stat-card"><h3>{key}</h3><div class="value">{value:,}</div></div>' for key, value in msg_distribution.items() if value > 0])}
            </div>
        </div>
        
        <!-- GROUP ANALYSIS -->
        {self._generate_groups_section(group_stats) if not group_stats.empty else ''}
        
        <!-- MEDIA ANALYSIS -->
        <div class="section">
            <h2 class="section-title">🎬 Media Analysis</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Photos</h3>
                    <div class="value">{media_stats.get('total_images', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Videos</h3>
                    <div class="value">{media_stats.get('total_videos', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Voice Notes</h3>
                    <div class="value">{media_stats.get('total_audio', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Documents</h3>
                    <div class="value">{media_stats.get('total_documents', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>GIFs</h3>
                    <div class="value">{media_stats.get('total_gifs', 0):,}</div>
                </div>
                <div class="stat-card">
                    <h3>Stickers</h3>
                    <div class="value">{media_stats.get('total_stickers', 0):,}</div>
                </div>
            </div>
            
            {self._generate_media_senders_table(top_media_senders) if not top_media_senders.empty else ''}
        </div>
        
        <!-- WORD ANALYSIS -->
        {self._generate_word_analysis_section(word_freq, wordcloud_img, msg_length)}
        
        <!-- EMOJI ANALYSIS -->
        {self._generate_emoji_section(emoji_stats) if not emoji_stats.empty else ''}
        
        <!-- MESSAGE DETAILS -->
        {self._generate_message_details_section(longest_messages, recent_messages, first_messages, response_time_stats)}
        
        <!-- CONVERSATIONS -->
        {self._generate_conversation_details_section(top_contacts)}
        
        <div class="footer">
            <p>🔒 This report is completely offline. Your data is private.</p>
            <p>📊 WhatsApp Database Analyzer | Developed with Python</p>
        </div>
    </div>
</body>
</html>
"""
        
        # HTML dosyasını kaydet
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Rapor başarıyla oluşturuldu: {self.output_file}")
        return self.output_file
    
    def _generate_contacts_table(self, contacts_df):
        """Kişiler tablosu HTML"""
        if contacts_df.empty:
            return '<p>Kişi verisi bulunamadı</p>'
        
        html = '<table><thead><tr>'
        html += '<th>Rank</th><th>Contact</th><th>Total Messages</th><th>Sent</th>'
        html += '<th>Received</th><th>Balance Score</th><th>Last Message</th></tr></thead><tbody>'
        
        for idx, row in contacts_df.head(20).iterrows():
            last_msg = row.get('last_message', '')
            if pd.notna(last_msg) and hasattr(last_msg, 'strftime'):
                last_msg = last_msg.strftime('%Y-%m-%d')
            
            html += f'''<tr>
                <td>{idx + 1}</td>
                <td><strong>{row.get("contact_name", "Unknown")}</strong></td>
                <td>{row.get("total_messages", 0):,}</td>
                <td style="color: #25D366;">{row.get("sent_by_me", 0):,}</td>
                <td style="color: #34B7F1;">{row.get("received", 0):,}</td>
                <td>{row.get("balance_score", 0):.2f}</td>
                <td>{last_msg}</td>
            </tr>'''
        
        html += '</tbody></table>'
        return html
    
    def _generate_groups_section(self, groups_df):
        """Groups section HTML"""
        if groups_df.empty:
            return ''
        
        html = '<div class="section"><h2 class="section-title">👥 Group Analysis</h2>'
        html += '<table><thead><tr><th>Rank</th><th>Group Name</th><th>Total Messages</th>'
        html += '<th>First Message</th><th>Last Message</th></tr></thead><tbody>'
        
        for idx, row in groups_df.head(20).iterrows():
            first_msg = row.get('first_message', '')
            last_msg = row.get('last_message', '')
            
            if pd.notna(first_msg) and hasattr(first_msg, 'strftime'):
                first_msg = first_msg.strftime('%Y-%m-%d')
            if pd.notna(last_msg) and hasattr(last_msg, 'strftime'):
                last_msg = last_msg.strftime('%Y-%m-%d')
            
            html += f'''<tr>
                <td>{idx + 1}</td>
                <td><strong>{row.get("group_name", "Unknown")}</strong></td>
                <td>{row.get("total_messages", 0):,}</td>
                <td>{first_msg}</td>
                <td>{last_msg}</td>
            </tr>'''
        
        html += '</tbody></table></div>'
        return html
    
    def _generate_media_senders_table(self, media_df):
        """Top media senders table"""
        if media_df.empty:
            return ''
        
        html = '<h3 style="color: #34B7F1; margin-top: 30px;">Top Media Senders</h3>'
        html += '<table><thead><tr><th>Rank</th><th>Contact</th><th>🖼️ Photos</th><th>🎵 Audio</th><th>🎥 Videos</th><th>📊 Total</th></tr></thead><tbody>'
        
        for idx, row in media_df.head(10).iterrows():
            contact_name = row.get('contact_name', 'Unknown')
            
            # If contact_name still looks like ID, get name from chat_id
            if pd.notna(contact_name) and (contact_name == 'Unknown' or '@' in str(contact_name) or str(contact_name).isdigit()):
                chat_id = row.get('chat_id', contact_name)
                contact_name = self.analyzer.get_contact_name(chat_id)
            
            images = int(row.get('images', 0))
            audio = int(row.get('audio', 0))
            videos = int(row.get('videos', 0))
            total = int(row.get('total_media', 0))
            
            html += f'''<tr>
                <td>{idx + 1}</td>
                <td><strong>{contact_name}</strong></td>
                <td>{images:,}</td>
                <td>{audio:,}</td>
                <td>{videos:,}</td>
                <td style="color: #25D366; font-weight: bold;">{total:,}</td>
            </tr>'''
        
        html += '</tbody></table>'
        return html
    
    def _generate_word_analysis_section(self, word_freq_df, wordcloud_img, msg_length):
        """Word analysis section"""
        html = '<div class="section"><h2 class="section-title">📖 Word Analysis</h2>'
        
        # Message length statistics
        if msg_length:
            html += '<div class="stats-grid">'
            html += f'<div class="stat-card"><h3>Average Length</h3><div class="value">{msg_length.get("average_length", 0):.1f}</div><div class="label">characters</div></div>'
            html += f'<div class="stat-card"><h3>Median Length</h3><div class="value">{msg_length.get("median_length", 0):.1f}</div><div class="label">characters</div></div>'
            html += f'<div class="stat-card"><h3>Longest Message</h3><div class="value">{msg_length.get("max_length", 0):,}</div><div class="label">characters</div></div>'
            html += '</div>'
        
        # Word cloud
        if wordcloud_img:
            html += '<h3 style="color: #34B7F1; margin-top: 30px;">Word Cloud</h3>'
            html += f'<div class="wordcloud-container"><img src="{wordcloud_img}" alt="Word Cloud"></div>'
        
        # Most used words
        if not word_freq_df.empty:
            html += '<h3 style="color: #34B7F1; margin-top: 30px;">Most Used Words</h3>'
            html += '<table><thead><tr><th>Rank</th><th>Word</th><th>Frequency</th></tr></thead><tbody>'
            
            for idx, row in word_freq_df.head(30).iterrows():
                html += f'''<tr>
                    <td>{idx + 1}</td>
                    <td><strong>{row["word"]}</strong></td>
                    <td>{row["frequency"]:,}</td>
                </tr>'''
            
            html += '</tbody></table>'
        
        html += '</div>'
        return html
    
    def _generate_emoji_section(self, emoji_df):
        """Emoji analysis section"""
        if emoji_df.empty:
            return ''
        
        html = '<div class="section"><h2 class="section-title">😊 Emoji Analysis</h2>'
        html += f'<p>Total <strong>{emoji_df["frequency"].sum():,}</strong> emojis used</p>'
        html += '<div class="emoji-grid">'
        
        for _, row in emoji_df.head(30).iterrows():
            html += f'''<div class="emoji-item">
                <div class="emoji">{row["emoji"]}</div>
                <div class="count">{row["frequency"]:,}</div>
            </div>'''
        
        html += '</div></div>'
        return html
    
    def _generate_message_details_section(self, longest_msgs, recent_msgs, first_msgs, response_stats):
        """Message details section"""
        html = '<div class="section"><h2 class="section-title">💬 Message Details</h2>'
        
        # Response times
        if response_stats:
            html += '<h3 style="color: #34B7F1;">⏱️ Response Times</h3>'
            html += '<div class="stats-grid">'
            html += f'<div class="stat-card"><h3>Average</h3><div class="value">{response_stats.get("avg_response_time_minutes", 0):.1f}</div><div class="label">minutes</div></div>'
            html += f'<div class="stat-card"><h3>Median</h3><div class="value">{response_stats.get("median_response_time_minutes", 0):.1f}</div><div class="label">minutes</div></div>'
            html += f'<div class="stat-card"><h3>Fastest</h3><div class="value">{response_stats.get("min_response_time_minutes", 0):.1f}</div><div class="label">minutes</div></div>'
            html += f'<div class="stat-card"><h3>Slowest</h3><div class="value">{response_stats.get("max_response_time_minutes", 0):.1f}</div><div class="label">minutes</div></div>'
            html += '</div>'
        
        # Longest messages
        if not longest_msgs.empty:
            html += '<h3 style="color: #34B7F1; margin-top: 30px;">📏 Longest Messages</h3>'
            html += '<div style="max-height: 400px; overflow-y: auto;">'
            for idx, row in longest_msgs.iterrows():
                text = str(row.get('text', ''))[:300]  # First 300 characters
                html += f'''<div style="background: #252525; padding: 15px; margin: 10px 0; border-radius: 10px; border-left: 3px solid #25D366;">
                    <div style="color: #888; font-size: 0.9em; margin-bottom: 5px;">Length: {row.get('length', 0)} characters</div>
                    <div style="color: #e0e0e0;">{text}...</div>
                </div>'''
            html += '</div>'
        
        # Recent messages
        if not recent_msgs.empty:
            html += '<h3 style="color: #34B7F1; margin-top: 30px;">🕐 Last Message from Each Contact</h3>'
            html += '<p style="color: #888; margin-bottom: 15px;">Your last message with each user</p>'
            html += '<div style="max-height: 500px; overflow-y: auto;">'
            for idx, row in recent_msgs.head(20).iterrows():
                from_me = row.get('from_me', 0)
                direction = "→ Sent" if from_me == 1 else "← Received"
                color = "#25D366" if from_me == 1 else "#34B7F1"
                
                chat_id = row.get('chat_id', 'Unknown')
                contact_name = self.analyzer.get_contact_name(chat_id)
                
                msg_text = str(row.get('message_text', ''))[:200] if pd.notna(row.get('message_text')) else '[Media]'
                datetime_str = row.get('datetime').strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row.get('datetime')) else ''
                
                html += f'''<div style="background: #252525; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 3px solid {color};">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: {color}; font-weight: bold;">{contact_name}</span>
                        <span style="color: #888; font-size: 0.85em;">{datetime_str}</span>
                    </div>
                    <div style="color: #888; font-size: 0.85em; margin-bottom: 5px;">{direction}</div>
                    <div style="color: #e0e0e0;">{msg_text}</div>
                </div>'''
            html += '</div>'
        
        # First messages
        if not first_msgs.empty:
            html += '<h3 style="color: #34B7F1; margin-top: 30px;">📅 First Message from Each Contact</h3>'
            html += '<p style="color: #888; margin-bottom: 15px;">Your first message with each user</p>'
            html += '<div style="max-height: 400px; overflow-y: auto;">'
            for idx, row in first_msgs.head(15).iterrows():
                from_me = row.get('from_me', 0)
                direction = "→ Sent" if from_me == 1 else "← Received"
                color = "#25D366" if from_me == 1 else "#34B7F1"
                
                chat_id = row.get('chat_id', 'Unknown')
                contact_name = self.analyzer.get_contact_name(chat_id)
                
                msg_text = str(row.get('message_text', ''))[:200] if pd.notna(row.get('message_text')) else '[Media]'
                datetime_str = row.get('datetime').strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row.get('datetime')) else ''
                
                html += f'''<div style="background: #252525; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 3px solid {color};">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: {color}; font-weight: bold;">{contact_name}</span>
                        <span style="color: #888; font-size: 0.85em;">{datetime_str}</span>
                    </div>
                    <div style="color: #888; font-size: 0.85em; margin-bottom: 5px;">{direction}</div>
                    <div style="color: #e0e0e0;">{msg_text}</div>
                </div>'''
            html += '</div>'
        
        html += '</div>'
        return html
    
    def _generate_conversation_details_section(self, top_contacts_df):
        """Contact-based conversation details - WhatsApp Web style"""
        if top_contacts_df.empty:
            return ''
        
        html = '<div class="section"><h2 class="section-title">💬 WhatsApp Web - Conversations</h2>'
        html += '<p style="margin-bottom: 20px;">Select a contact from the left, see the conversation on the right</p>'
        
        # WhatsApp Web style container
        html += '<div class="whatsapp-container">'
        
        # Left side - Contact list
        html += '<div class="contacts-sidebar">'
        html += '<div style="padding: 20px; background: #128C7E; color: white; font-weight: bold;">Conversations</div>'
        
        # JavaScript için konuşma verileri
        conversations_data = {}
        
        # Her kişi için kişi listesinde item oluştur
        for idx, row in top_contacts_df.head(15).iterrows():
            chat_id = row.get('chat_id', '')
            contact_name = row.get('contact_name', 'Unknown')
            total_messages = row.get('total_messages', 0)
            
            # Detaylı bilgileri al
            details = self.analyzer.get_conversation_details_for_contact(chat_id)
            
            if not details:
                continue
            
            # Son mesajın önizlemesi
            conversation = self.analyzer.get_conversation_with_contact(chat_id, limit=200)
            
            last_msg_preview = ""
            if not conversation.empty:
                last_msg = conversation.iloc[-1]
                last_msg_text = str(last_msg.get('message_text', ''))[:50] if pd.notna(last_msg.get('message_text')) else '[Medya]'
                last_msg_preview = last_msg_text
            
            # Kişi listesi item'ı
            contact_id = f"contact_{idx}"
            active_class = "active" if idx == 0 else ""
            
            html += f'''<div class="contact-item {active_class}" onclick="showConversation('{contact_id}')">
                <div class="name">{contact_name}</div>
                <div class="preview">{last_msg_preview}</div>
                <div class="count">{total_messages:,} messages</div>
            </div>'''
            
            # Konuşma verilerini sakla (datetime'ları string'e çevir)
            details_json = {
                'total_messages': details.get('total_messages', 0),
                'sent_by_me': details.get('sent_by_me', 0),
                'received': details.get('received', 0),
                'media_count': details.get('media_count', 0),
                'first_message': str(details.get('first_message', 'N/A')),
                'last_message': str(details.get('last_message', 'N/A')),
                'avg_message_length': float(details.get('avg_message_length', 0)),
            }
            
            conversations_data[contact_id] = {
                'name': contact_name,
                'details': details_json,
                'messages': []
            }
            
            # Mesajları JSON formatında hazırla
            if not conversation.empty:
                for _, msg in conversation.iterrows():
                    from_me = int(msg.get('from_me', 0))
                    msg_text = str(msg.get('message_text', ''))[:500] if pd.notna(msg.get('message_text')) else None
                    media_type = msg.get('media_type', 0)
                    datetime_str = msg.get('datetime').strftime('%Y-%m-%d %H:%M') if pd.notna(msg.get('datetime')) else ''
                    
                    conversations_data[contact_id]['messages'].append({
                        'from_me': from_me,
                        'text': msg_text,
                        'media_type': int(media_type) if pd.notna(media_type) else 0,
                        'time': datetime_str
                    })
        
        html += '</div>'  # contacts-sidebar sonu
        
        # Sağ taraf - Chat alanı
        html += '<div class="chat-area">'
        html += '<div class="chat-header" id="chatHeader">'
        
        # İlk kişiyi göster
        if conversations_data:
            first_contact = list(conversations_data.keys())[0]
            first_data = conversations_data[first_contact]
            html += f'''<div class="name">{first_data['name']}</div>
                <div class="info">
                    {first_data['details'].get('total_messages', 0)} messages • 
                    Sent: {first_data['details'].get('sent_by_me', 0)} • 
                    Received: {first_data['details'].get('received', 0)} • 
                    Media: {first_data['details'].get('media_count', 0)}
                </div>'''
        
        html += '</div>'
        
        # Mesaj alanı
        html += '<div class="chat-messages" id="chatMessages">'
        
        # İlk kişinin mesajlarını göster
        if conversations_data:
            first_contact = list(conversations_data.keys())[0]
            first_messages = conversations_data[first_contact]['messages']
            
            for msg in first_messages:
                msg_class = "sent" if msg['from_me'] == 1 else "received"
                
                if msg['text']:
                    msg_text = msg['text'].replace('<', '&lt;').replace('>', '&gt;')
                else:
                    media_types = {0: 'Text', 1: '🖼️ Photo', 2: '🎵 Audio', 3: '🎥 Video', 
                                  4: '👤 Contact', 5: '📍 Location', 9: '📄 Document', 13: 'GIF', 20: '🎨 Sticker'}
                    msg_text = f'<span class="media-indicator">{media_types.get(msg["media_type"], "Media")}</span>'
                
                html += f'''<div class="message-bubble {msg_class}">
                    <div class="message-content">
                        <div class="message-text">{msg_text}</div>
                        <div class="message-time">{msg['time']}</div>
                    </div>
                </div>'''
        
        html += '</div>'  # chat-messages sonu
        html += '</div>'  # chat-area sonu
        html += '</div>'  # whatsapp-container sonu
        
        # JavaScript kodu
        html += '''
        <script>
        // Konuşma verileri
        const conversationsData = ''' + json.dumps(conversations_data, ensure_ascii=False) + ''';
        
        function showConversation(contactId) {
            // Tüm kişilerin active class'ını kaldır
            document.querySelectorAll('.contact-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Tıklanan kişiyi active yap
            event.currentTarget.classList.add('active');
            
            // Konuşma verilerini al
            const data = conversationsData[contactId];
            if (!data) return;
            
            // Header'ı güncelle
            const header = document.getElementById('chatHeader');
            header.innerHTML = `
                <div class="name">${data.name}</div>
                <div class="info">
                    ${data.details.total_messages} messages • 
                    Sent: ${data.details.sent_by_me} • 
                    Received: ${data.details.received} • 
                    Media: ${data.details.media_count}
                </div>
            `;
            
            // Mesajları güncelle
            const messagesArea = document.getElementById('chatMessages');
            messagesArea.innerHTML = '';
            
            const mediaTypes = {
                0: 'Text', 1: '🖼️ Photo', 2: '🎵 Audio', 3: '🎥 Video',
                4: '👤 Contact', 5: '📍 Location', 9: '📄 Document', 13: 'GIF', 20: '🎨 Sticker'
            };
            
            data.messages.forEach(msg => {
                const msgClass = msg.from_me === 1 ? 'sent' : 'received';
                let msgText;
                
                if (msg.text) {
                    msgText = msg.text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                } else {
                    const mediaType = mediaTypes[msg.media_type] || 'Medya';
                    msgText = `<span class="media-indicator">${mediaType}</span>`;
                }
                
                const bubble = document.createElement('div');
                bubble.className = `message-bubble ${msgClass}`;
                bubble.innerHTML = `
                    <div class="message-content">
                        <div class="message-text">${msgText}</div>
                        <div class="message-time">${msg.time}</div>
                    </div>
                `;
                messagesArea.appendChild(bubble);
            });
            
            // En alta scroll
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
        
        // Sayfa yüklendiğinde ilk konuşmayı göster
        window.addEventListener('DOMContentLoaded', () => {
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        });
        </script>
        '''
        
        html += '</div>'  # section sonu
        return html


def test_report_generator():
    """Test fonksiyonu"""
    print("=== HTML Rapor Oluşturucu Test ===")
    print("Ana programdan çalıştırılmalıdır")


if __name__ == "__main__":
    test_report_generator()

