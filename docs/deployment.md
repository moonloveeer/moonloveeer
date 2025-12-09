# QRL Deployment Guide

## Overview
This guide covers deploying the QRL Web Wallet to production.

## Prerequisites
- Python 3.12+
- PostgreSQL (for production)
- Redis (for caching)
- Nginx (reverse proxy)
- SSL certificate

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/moonloveeer/moonloveeer.git
cd moonloveeer
```

### 2. Set Up Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with production values
```

Required environment variables:
```env
SECRET_KEY=your_random_secret_key_here
WEB_WALLET_DATA_DIR=/var/lib/qrl/wallet
QRL_LIVE_MODE=true
AUTO_MINE_ON_SEND=false

# Coinbase Commerce
COINBASE_COMMERCE_API_KEY=your_api_key
COINBASE_WEBHOOK_SECRET=your_webhook_secret
QRL_PRICE_USD=0.10

# Database
DATABASE_URL=postgresql://user:pass@localhost/qrl

# Redis
REDIS_URL=redis://localhost:6379/0

# SSL
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

## Database Setup

### PostgreSQL
```bash
sudo -u postgres createdb qrl
sudo -u postgres createuser qrl
sudo -u postgres psql -c "ALTER USER qrl PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE qrl TO qrl;"
```

### Redis
```bash
sudo apt-get install redis-server
sudo systemctl enable redis
sudo systemctl start redis
```

## Web Server Configuration

### Nginx
Create `/etc/nginx/sites-available/qrl`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/qrl /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Application Server

### Gunicorn
Create `gunicorn.conf.py`:
```python
bind = "127.0.0.1:5001"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### Systemd Service
Create `/etc/systemd/system/qrl.service`:
```ini
[Unit]
Description=QRL Web Wallet
After=network.target

[Service]
Type=notify
User=qrl
Group=qrl
RuntimeDirectory=qrl
WorkingDirectory=/opt/qrl
Environment=PATH=/opt/qrl/venv/bin
ExecStart=/opt/qrl/venv/bin/gunicorn -c gunicorn.conf.py qrl.web_wallet:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable qrl
sudo systemctl start qrl
```

## Security Configuration

### Firewall
```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### SSL Certificate (Let's Encrypt)
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Hardening
- Disable debug mode
- Set secure headers
- Configure rate limiting
- Set up log rotation
- Enable fail2ban

## Monitoring

### Log Monitoring
```bash
# Application logs
tail -f /var/log/qrl/app.log

# Security logs
tail -f /var/lib/qrl/wallet/security.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Health Checks
Create health check endpoint:
```python
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': VERSION
    })
```

## Backup Strategy

### Database Backup
```bash
#!/bin/bash
# backup_db.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U qrl qrl > /backup/qrl_$DATE.sql
find /backup -name "qrl_*.sql" -mtime +7 -delete
```

### Wallet Data Backup
```bash
#!/bin/bash
# backup_wallet.sh
rsync -av /var/lib/qrl/wallet/ /backup/wallet/
```

## Scaling Considerations

### Horizontal Scaling
- Use load balancer (HAProxy/Nginx)
- Shared session storage (Redis)
- Database replication

### Performance Optimization
- Enable Redis caching
- Use CDN for static assets
- Optimize database queries
- Implement connection pooling

## Troubleshooting

### Common Issues
1. **Service won't start**: Check logs, verify permissions
2. **Database connection failed**: Verify credentials, check PostgreSQL status
3. **High memory usage**: Reduce worker count, enable memory limits
4. **Slow response times**: Check database performance, enable caching

### Debug Commands
```bash
# Check service status
sudo systemctl status qrl

# View logs
sudo journalctl -u qrl -f

# Test application
curl -I http://localhost:5001/health

# Check database
psql -h localhost -U qrl -d qrl -c "SELECT 1;"
```

## Maintenance

### Regular Tasks
- Update dependencies monthly
- Rotate secrets quarterly
- Review logs weekly
- Update SSL certificate before expiry
- Test backup restoration monthly

### Updates
```bash
# Pull updates
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart qrl
```
