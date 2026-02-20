# Eurojackpot Analyse & Simulation

Streamlit-Dashboard zur statistischen Analyse von Eurojackpot-Ziehungen.

---

## Deployment auf Hetzner Ubuntu VPS (mit Nginx)

Getestet auf **Ubuntu 22.04 / 24.04 LTS**. Anleitung geht von einem frischen Server aus.

---

### 1. Server-Grundkonfiguration

```bash
# System updaten
sudo apt update && sudo apt upgrade -y

# Grundpakete installieren
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx ufw
```

### 2. Firewall einrichten

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

> **Wichtig:** In der Hetzner Cloud Console unter **Firewalls** zusätzlich Port 80 (HTTP) und 443 (HTTPS) freigeben, falls eine Hetzner-Firewall aktiv ist.

### 3. Projekt auf den Server bringen

```bash
# Projektordner anlegen
sudo mkdir -p /opt/jackpot
sudo chown $USER:$USER /opt/jackpot

# Dateien hochladen (von deinem lokalen Rechner aus)
# Option A: scp
scp -r app.py combine_eurojackpot.py requirements.txt *.xlsx benutzer@DEINE-SERVER-IP:/opt/jackpot/

# Option B: Git (falls du ein Repo hast)
cd /opt/jackpot
git clone https://github.com/DEIN-USER/jackpot.git .
```

### 4. Python-Umgebung einrichten

```bash
cd /opt/jackpot

# Virtuelle Umgebung erstellen und aktivieren
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Daten vorbereiten (falls Alle_Eurojackpot_Zahlen.xlsx noch nicht existiert)
python combine_eurojackpot.py
```

### 5. Streamlit-Konfiguration

```bash
mkdir -p /opt/jackpot/.streamlit
```

```bash
cat > /opt/jackpot/.streamlit/config.toml << 'EOF'
[server]
headless = true
port = 8501
address = "127.0.0.1"
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
EOF
```

> Streamlit lauscht nur auf `127.0.0.1` — von außen ist es **nicht direkt erreichbar**. Nginx leitet den Traffic weiter.

### 6. Systemd-Service erstellen

Damit Streamlit automatisch startet und nach Abstürzen neustartet:

```bash
sudo cat > /etc/systemd/system/jackpot.service << 'EOF'
[Unit]
Description=Eurojackpot Streamlit App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/jackpot
ExecStart=/opt/jackpot/venv/bin/streamlit run app.py
Restart=always
RestartSec=5
Environment="PATH=/opt/jackpot/venv/bin:/usr/bin"

[Install]
WantedBy=multi-user.target
EOF
```

```bash
# Service aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable jackpot
sudo systemctl start jackpot

# Status prüfen
sudo systemctl status jackpot
```

**Nützliche Service-Befehle:**

```bash
sudo systemctl restart jackpot   # Neustart
sudo systemctl stop jackpot      # Stoppen
sudo journalctl -u jackpot -f    # Live-Logs ansehen
```

### 7. Nginx als Reverse Proxy

#### 7a. Konfiguration erstellen

Ersetze `deine-domain.de` mit deiner echten Domain (oder der Server-IP, wenn du keine Domain hast).

```bash
sudo cat > /etc/nginx/sites-available/jackpot << 'EOF'
server {
    listen 80;
    server_name deine-domain.de;

    # Weiterleitung an Streamlit
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;

        # WebSocket-Support (Streamlit braucht das)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts großzügig setzen (Streamlit kann langsam laden)
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Streamlit Health-Check Endpoint
    location /_stcore/health {
        proxy_pass http://127.0.0.1:8501/_stcore/health;
    }
}
EOF
```

#### 7b. Site aktivieren

```bash
# Symlink erstellen
sudo ln -sf /etc/nginx/sites-available/jackpot /etc/nginx/sites-enabled/

# Default-Site deaktivieren (optional)
sudo rm -f /etc/nginx/sites-enabled/default

# Konfiguration testen
sudo nginx -t

# Nginx neustarten
sudo systemctl restart nginx
```

Jetzt sollte die App unter `http://deine-domain.de` erreichbar sein.

### 8. SSL mit Let's Encrypt (HTTPS)

> Voraussetzung: Eine Domain, die auf die Server-IP zeigt (A-Record im DNS).

```bash
sudo certbot --nginx -d deine-domain.de
```

Certbot passt die Nginx-Konfiguration automatisch an und richtet die HTTPS-Weiterleitung ein.

**Automatische Zertifikatserneuerung testen:**

```bash
sudo certbot renew --dry-run
```

Certbot richtet automatisch einen Timer ein, der das Zertifikat vor Ablauf erneuert.

### 9. Ohne Domain (nur IP-Zugriff)

Falls du keine Domain hast, überspringe Schritt 8 und ersetze `deine-domain.de` in der Nginx-Config durch:

```
server_name _;
```

Die App ist dann unter `http://DEINE-SERVER-IP` erreichbar.

---

## Updates deployen

```bash
# Neue Dateien hochladen (scp oder git pull)
cd /opt/jackpot
git pull  # oder scp ...

# Venv aktualisieren (falls sich requirements.txt geändert hat)
source venv/bin/activate
pip install -r requirements.txt

# App neustarten
sudo systemctl restart jackpot
```

## Troubleshooting

| Problem | Lösung |
|---|---|
| App startet nicht | `sudo journalctl -u jackpot -n 50` prüfen |
| 502 Bad Gateway | Streamlit läuft nicht → `sudo systemctl status jackpot` |
| WebSocket-Fehler im Browser | Nginx-Config prüfen (Upgrade-Header fehlt) |
| Excel-Datei nicht gefunden | `ls /opt/jackpot/Alle_Eurojackpot_Zahlen.xlsx` — ggf. `python combine_eurojackpot.py` ausführen |
| Port 8501 belegt | `sudo ss -tlnp | grep 8501` prüfen |
| Certbot schlägt fehl | DNS-A-Record prüfen, Port 80 muss offen sein |

## Projektstruktur

```
/opt/jackpot/
├── app.py                        # Streamlit-Hauptanwendung
├── combine_eurojackpot.py        # Daten-Vorbereitungsskript
├── requirements.txt              # Python-Abhängigkeiten
├── Alle_Eurojackpot_Zahlen.xlsx  # Kombinierte Ziehungsdaten
├── EJ_ab_2022.xlsx               # Rohdaten ab 2022
├── EJ_bis_2021.xlsx              # Rohdaten bis 2021
├── venv/                         # Python Virtual Environment
└── .streamlit/
    └── config.toml               # Streamlit-Konfiguration
```
# jackpot
