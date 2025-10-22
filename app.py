import time
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime
import os
from flask import Flask

app = Flask(__name__)

class ServerTradingBot:
    def __init__(self):
        self.BOT_TOKEN = "8276095316:AAEWEpp_o3-IQuudqB9AwjrK3nU9ta8Gv_Q"
        self.CHAT_ID = "8041753205"
        self.running = True
        
        # عملات بينانس الرئيسية
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "XRPUSDT"]
        
        # إعدادات السيرفر
        self.cycle_count = 0
        self.start_time = datetime.now()

    def get_price_data(self, symbol, interval='15m', limit=50):
        """جلب بيانات الأسعار من بينانس"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'ignore', 'ignore', 'ignore'
                ])
                
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                return df
        except Exception as e:
            print(f"❌ خطأ في جلب البيانات: {e}")
        return None

    def advanced_analysis(self, symbol):
        """تحليل متقدم للعملة"""
        try:
            df = self.get_price_data(symbol)
            if df is None or len(df) < 20:
                return None
            
            # مؤشرات متقدمة
            df['rsi'] = self.calculate_rsi(df['close'])
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            
            current_price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            sma_20 = df['sma_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            
            # استراتيجية متقدمة
            signals = []
            
            # استراتيجية RSI
            if rsi < 30:
                signals.append(('BUY', 8.5 + (30 - rsi) * 0.1, 'RSI Oversold'))
            elif rsi > 70:
                signals.append(('SELL', 8.5 + (rsi - 70) * 0.1, 'RSI Overbought'))
            
            # استراتيجية المتوسطات
            if sma_20 > sma_50 and df['sma_20'].iloc[-2] <= df['sma_50'].iloc[-2]:
                signals.append(('BUY', 8.8, 'Golden Cross'))
            elif sma_20 < sma_50 and df['sma_20'].iloc[-2] >= df['sma_50'].iloc[-2]:
                signals.append(('SELL', 8.8, 'Death Cross'))
            
            # استراتيجية الزخم
            price_change = (current_price - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
            if abs(price_change) > 3:
                if price_change > 0:
                    signals.append(('BUY', 8.3, f'Momentum +{price_change:.1f}%'))
                else:
                    signals.append(('SELL', 8.3, f'Momentum {price_change:.1f}%'))
            
            if signals:
                # اختيار أقوى إشارة
                best_signal = max(signals, key=lambda x: x[1])
                return {
                    'symbol': symbol,
                    'signal': best_signal[0],
                    'confidence': best_signal[1],
                    'strategy': best_signal[2],
                    'current_price': current_price,
                    'rsi': rsi
                }
                
        except Exception as e:
            print(f"❌ خطأ في التحليل: {e}")
        return None

    def calculate_rsi(self, prices, period=14):
        """حساب مؤشر RSI"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = pd.Series(gains).rolling(period).mean()
        avg_losses = pd.Series(losses).rolling(period).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def send_telegram_message(self, message):
        """إرسال رسالة للتليجرام"""
        url = f"https://api.telegram.org/bot{self.BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': self.CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ خطأ في الإرسال: {e}")
            return False

    def format_signal_message(self, analysis):
        """تنسيق رسالة الإشارة"""
        signal_icon = "🟢" if analysis['signal'] == 'BUY' else "🔴"
        signal_text = "شراء قوي" if analysis['signal'] == 'BUY' else "بيع قوي"
        
        message = f"{signal_icon} **إشارة تداول من السيرفر** {signal_icon}\n\n"
        message += f"💰 **العملة:** {analysis['symbol']}\n"
        message += f"📊 **السعر الحالي:** ${analysis['current_price']:.4f}\n"
        message += f"🎯 **الإشارة:** {signal_text}\n"
        message += f"⭐ **الثقة:** {analysis['confidence']:.1f}/10\n"
        message += f"🧠 **الاستراتيجية:** {analysis['strategy']}\n"
        message += f"📈 **RSI:** {analysis['rsi']:.1f}\n\n"
        
        # حساب التوصيات
        if analysis['signal'] == 'BUY':
            entry = analysis['current_price'] * 0.998
            stop_loss = entry * 0.985
            take_profit = entry * 1.025
        else:
            entry = analysis['current_price'] * 1.002
            stop_loss = entry * 1.015
            take_profit = entry * 0.975
        
        message += "📋 **التوصيات:**\n"
        message += f"• 🎯 الدخول: ${entry:.4f}\n"
        message += f"• 🛑 وقف الخسارة: ${stop_loss:.4f}\n"
        message += f"• 🎯 جني الربح: ${take_profit:.4f}\n"
        message += f"• ⚖️ المخاطرة: 1:2.0\n\n"
        
        message += f"⏰ **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"🖥️ **السيرفر:** Render (24/7)\n"
        message += "=" * 40
        
        return message

    def start_server_operation(self):
        """بدء التشغيل على السيرفر"""
        print("🚀 بدء تشغيل البوت على السيرفر...")
        self.send_telegram_message(
            "🤖 **بدء التشغيل على السيرفر**\n\n"
            "🖥️ البوت يعمل الآن على Render\n"
            "⏰ تشغيل مستمر 24/7\n"
            "📊 مراقبة تلقائية للأسواق\n"
            "🎯 إشارات ذكية تلقائية\n\n"
            "✅ جاري المسح الأول..."
        )
        
        while self.running:
            try:
                self.cycle_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"🔍 [{current_time}] الدورة رقم: {self.cycle_count}")
                
                # تحليل جميع العملات
                strong_signals = []
                
                for symbol in self.symbols:
                    analysis = self.advanced_analysis(symbol)
                    if analysis and analysis['confidence'] >= 8.0:
                        strong_signals.append(analysis)
                        print(f"✅ إشارة قوية: {symbol}")
                
                # إرسال أفضل إشارة
                if strong_signals:
                    best_signal = max(strong_signals, key=lambda x: x['confidence'])
                    message = self.format_signal_message(best_signal)
                    
                    if self.send_telegram_message(message):
                        print(f"📨 تم إرسال إشارة: {best_signal['symbol']}")
                
                # إرسال تقرير كل 10 دورات
                if self.cycle_count % 10 == 0:
                    uptime = datetime.now() - self.start_time
                    report = (
                        f"📊 **تقرير السيرفر الدوري**\n\n"
                        f"🔄 عدد الدورات: {self.cycle_count}\n"
                        f"⏰ وقت التشغيل: {str(uptime).split('.')[0]}\n"
                        f"📈 آخر إشارة: {len(strong_signals)} إشارة قوية\n"
                        f"🖥️ حالة السيرفر: ✅ نشط\n\n"
                        f"⏳ جاري الاستمرار في المراقبة..."
                    )
                    self.send_telegram_message(report)
                
                # انتظار 5 دقائق بين الدورات
                time.sleep(300)
                
            except Exception as e:
                print(f"❌ خطأ في الدورة: {e}")
                # إعادة المحاولة بعد دقيقة
                time.sleep(60)

# إنشاء البوت
bot = ServerTradingBot()

@app.route('/')
def home():
    """الصفحة الرئيسية"""
    uptime = datetime.now() - bot.start_time
    return f"""
    <html>
        <head>
            <title>تداول البوت الذكي</title>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; text-align: center; direction: rtl;">
            <h1>🤖 بوت التداول الذكي</h1>
            <p>يعمل على السيرفر 24/7</p>
            <div style="background: #f0f0f0; padding: 20px; margin: 20px; border-radius: 10px;">
                <h3>📊 إحصائيات التشغيل:</h3>
                <p>🔄 عدد الدورات: {bot.cycle_count}</p>
                <p>⏰ وقت التشغيل: {str(uptime).split('.')[0]}</p>
                <p>🖥️ الحالة: ✅ نشط</p>
            </div>
            <p>البوت يراقب الأسواق تلقائياً ويرسل إشارات التداول</p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    """نقطة فحص الصحة"""
    return {"status": "healthy", "cycles": bot.cycle_count, "uptime": str(datetime.now() - bot.start_time)}

@app.route('/start')
def start_bot():
    """بدء البوت"""
    import threading
    thread = threading.Thread(target=bot.start_server_operation)
    thread.daemon = True
    thread.start()
    return {"status": "Bot started"}

if __name__ == '__main__':
    # بدء البوت في thread منفصل
    import threading
    bot_thread = threading.Thread(target=bot.start_server_operation)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل الخادم
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)