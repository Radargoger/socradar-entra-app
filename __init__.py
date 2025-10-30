import os
import json
import logging
import requests
import datetime
import azure.functions as func

# Ortam değişkenlerinden kimlik bilgilerini ve URL'leri çek
# Bu değerler ARM şablonunuzda Application Settings olarak tanımlandı.
TENANT_ID = os.environ.get("TENANT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
SOCRADAR_API_URL = os.environ.get("SOCRADAR_API_URL")
SOCRADAR_API_KEY = os.environ.get("SOCRADAR_API_KEY")

# Microsoft Graph API endpoint'leri
SCOPE = "https://graph.microsoft.com/.default"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# --- Graph API Helper Fonksiyonları ---

def get_access_token() -> str | None:
    """
    Client Credentials Akışını kullanarak bir Access Token alır.
    """
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        logging.error("Yapılandırma hatası: Tenant ID, Client ID, veya Secret eksik.")
        return None

    data = {
        "client_id": CLIENT_ID,
        "scope": SCOPE,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erişim Belirteci isteği başarısız oldu: {e}")
        return None

def fetch_graph_data(access_token: str, hours: int = 1) -> list:
    """
    Graph API'den son 'hours' saatlik oturum açma kayıtlarını çeker.
    """
    # Son çalıştırmadan bu yana geçen süreyi hesaplamak için basit bir filtre
    time_filter = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).isoformat() + "Z"
    
    # Oturum açma (Sign-in) kayıtlarını çekmek için gerekli Graph API ucu
    graph_endpoint = f"{GRAPH_API_BASE}/auditLogs/signIns"
    
    # Sadece ilgili verileri çekmek için $filter ve $select kullanın
    query = f"?$filter=createdDateTime ge {time_filter}&$select=id,createdDateTime,userPrincipalName,ipAddress,appDisplayName,status"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    logging.info(f"Graph API sorgusu: {graph_endpoint}{query}")

    try:
        response = requests.get(graph_endpoint + query, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])
    except requests.exceptions.RequestException as e:
        logging.error(f"Graph API veri çekme başarısız oldu: {e}")
        return []

# --- SocRadar Helper Fonksiyonları ---

def send_to_socradar(data: list) -> bool:
    """
    İşlenmiş verileri SocRadar API'sine gönderir.
    """
    if not all([SOCRADAR_API_URL, SOCRADAR_API_KEY]):
        logging.warning("SocRadar URL veya API Anahtarı eksik. Gönderme adımı atlandı.")
        return False
    
    # Gerçek entegrasyonda, Graph verilerini SocRadar'ın beklediği formata dönüştürün.
    # Burada basitçe tüm veriyi gönderiyoruz.
    socradar_payload = {
        "source": "AzureEntraID",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "events": data 
    }

    logging.info(f"SocRadar'a {len(data)} olay gönderiliyor.")
    
    socradar_headers = {
        "Content-Type": "application/json",
        "X-API-KEY": SOCRADAR_API_KEY # SocRadar'ın istediği kimlik doğrulama başlığı
    }

    try:
        response = requests.post(SOCRADAR_API_URL, json=socradar_payload, headers=socradar_headers)
        response.raise_for_status()
        logging.info("Veriler SocRadar'a başarıyla gönderildi.")
        # SocRadar'ın başarılı cevabını (genellikle 200 veya 202) logla
        logging.info(f"SocRadar yanıtı: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"SocRadar API'ye gönderme başarısız oldu: {e}. Yanıt: {getattr(e.response, 'text', 'Yanıt Yok')}")
        return False

# --- Ana Function Giriş Noktası ---

def main(mytimer: func.TimerRequest) -> None:
    """
    Azure Function ana yürütme noktası.
    """
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    logging.info(f'Python Timer trigger function started at {utc_timestamp}')

    # 1. Erişim Belirteci (Access Token) Al
    access_token = get_access_token()
    if not access_token:
        logging.error("İşlem durduruldu: Erişim belirteci alınamadı.")
        return

    # 2. Microsoft Graph'tan Veri Çek
    # Not: Timer Trigger her 5 dakikada bir çalıştırılacaksa, veri kaybını önlemek için 
    # son 5 dakikalık veriyi çekmelisiniz. (Burada güvenlik için 1 saat bırakıldı, 
    # cron ifadesi 5 dakikada bir çalışacaksa 'hours=0.08' yapabilirsiniz.
    entra_data = fetch_graph_data(access_token, hours=1) 
    
    if entra_data:
        # 3. Verileri SocRadar'a Gönder
        success = send_to_socradar(entra_data)
        if success:
            logging.info(f"Görev başarıyla tamamlandı. {len(entra_data)} olay SocRadar'a iletildi.")
        else:
            logging.error("Veri iletimi sırasında bir hata oluştu.")
    else:
        logging.info("Çekilecek yeni Entra ID kaydı bulunamadı.")
        
    logging.info(f'Python Timer trigger function finished at {datetime.datetime.utcnow().isoformat()}')