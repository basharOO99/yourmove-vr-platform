# YourMove - Deployment Guide

Complete guide for deploying YourMove VR Therapy Platform to production environments.

## 📋 Pre-Deployment Checklist

Before deploying to production, ensure you:

- [ ] Update `SECRET_KEY` in `auth.py` or use environment variable
- [ ] Configure allowed CORS origins in production
- [ ] Test all features locally
- [ ] Review database setup
- [ ] Prepare environment variables
- [ ] Test WebSocket connections
- [ ] Verify API endpoints work correctly

## 🚀 Deployment Options

### Option 1: Koyeb (Recommended - Free Tier Available)

#### Step 1: Prepare Your Repository

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - YourMove v2.0"

# Create repository on GitHub
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/yourmove.git
git branch -M main
git push -u origin main
```

#### Step 2: Deploy to Koyeb

1. **Sign up** at [koyeb.com](https://www.koyeb.com)

2. **Create New Service**
   - Click "Create Service"
   - Select "GitHub" as deployment method
   - Authorize Koyeb to access your repositories
   - Select your `yourmove` repository

3. **Configure Build**
   - **Builder**: Buildpack
   - **Build command**: (leave empty, auto-detected)
   - **Run command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Configure Environment**
   - **Name**: yourmove-vr-therapy
   - **Region**: Choose closest to your users
   - **Instance type**: Free or Eco (recommended)

5. **Add Environment Variables**
   ```
   SECRET_KEY=your-super-secret-key-32-chars-minimum
   DATABASE_URL=sqlite:///./yourmove.db
   LOG_LEVEL=INFO
   ```

6. **Deploy**
   - Click "Deploy"
   - Wait 2-3 minutes for deployment
   - Your app will be available at: `https://your-app-name.koyeb.app`

#### Step 3: Verify Deployment

1. Visit your app URL
2. Test login at `/login`
3. Check dashboard functionality
4. Verify WebSocket connections work

### Option 2: Heroku

#### Prerequisites
- Heroku account
- Heroku CLI installed

#### Deployment Steps

```bash
# Login to Heroku
heroku login

# Create new app
heroku create yourmove-vr-therapy

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DATABASE_URL=sqlite:///./yourmove.db

# Deploy
git push heroku main

# Open app
heroku open
```

### Option 3: Railway

#### Deployment Steps

1. **Sign up** at [railway.app](https://railway.app)
2. **New Project** → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects settings
5. **Add Environment Variables**:
   ```
   SECRET_KEY=your-secret-key
   PORT=8000
   ```
6. Deploy automatically starts

### Option 4: Render

#### Deployment Steps

1. **Sign up** at [render.com](https://render.com)
2. **New Web Service** → Connect GitHub
3. **Settings**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment Variables**:
   ```
   SECRET_KEY=your-secret-key
   PYTHON_VERSION=3.9.18
   ```
5. Click "Create Web Service"

### Option 5: DigitalOcean App Platform

#### Deployment Steps

1. **Sign up** at [digitalocean.com](https://www.digitalocean.com/products/app-platform)
2. **Create App** → Select GitHub repository
3. **Configure**:
   - **Type**: Web Service
   - **Run Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **HTTP Port**: 8000
4. **Environment Variables**:
   ```
   SECRET_KEY=your-secret-key
   ```
5. Deploy

### Option 6: Docker + Any Cloud Provider

#### Create Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Build and Deploy

```bash
# Build image
docker build -t yourmove:latest .

# Run locally for testing
docker run -p 8000:8000 yourmove:latest

# Tag for registry (e.g., Docker Hub)
docker tag yourmove:latest yourusername/yourmove:latest

# Push to registry
docker push yourusername/yourmove:latest

# Deploy to cloud provider using container registry
```

### Option 7: AWS EC2 (Manual)

#### Prerequisites
- AWS account
- EC2 instance (Ubuntu 20.04+)

#### Deployment Steps

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3.9 python3-pip -y

# Install nginx
sudo apt install nginx -y

# Clone repository
git clone https://github.com/YOUR_USERNAME/yourmove.git
cd yourmove

# Install dependencies
pip3 install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/yourmove.service
```

**Service file content**:
```ini
[Unit]
Description=YourMove VR Therapy Platform
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/yourmove
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable yourmove
sudo systemctl start yourmove

# Configure nginx as reverse proxy
sudo nano /etc/nginx/sites-available/yourmove
```

**Nginx config**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/yourmove /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Set up SSL with Let's Encrypt (optional)
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

## 🔐 Production Security Checklist

Before going live, ensure:

- [ ] Change default admin password
- [ ] Use strong SECRET_KEY (32+ random characters)
- [ ] Enable HTTPS/WSS for WebSocket connections
- [ ] Configure CORS to allow only your domain
- [ ] Set up rate limiting
- [ ] Enable logging and monitoring
- [ ] Regular database backups
- [ ] Use environment variables for secrets
- [ ] Implement API key rotation
- [ ] Set up firewall rules
- [ ] Enable automatic security updates

## 📊 Post-Deployment

### Monitoring

1. **Check Application Status**
   ```bash
   curl https://your-app.com/health
   ```

2. **Monitor Logs** (varies by platform)
   - Koyeb: Check in dashboard
   - Heroku: `heroku logs --tail`
   - Railway: View in dashboard
   - EC2: `sudo journalctl -u yourmove -f`

### Testing

1. Visit landing page
2. Test doctor login
3. Create test patient
4. Simulate WebSocket connection
5. Check dashboard updates

### Updating

```bash
# Make changes locally
git add .
git commit -m "Update description"
git push origin main

# Most platforms auto-deploy on push
# For manual deployments, repeat deployment steps
```

## 🐛 Troubleshooting

### WebSocket Issues
- Ensure WSS (not WS) for HTTPS sites
- Check proxy configuration supports WebSocket
- Verify timeout settings

### Database Issues
- For SQLite in production, consider PostgreSQL
- Ensure database file permissions
- Set up regular backups

### Performance Issues
- Increase worker count: `--workers 4`
- Enable caching
- Optimize database queries
- Use CDN for static assets

## 📞 Support

For deployment issues:
1. Check platform-specific documentation
2. Review application logs
3. Test locally first
4. Verify all environment variables

## 🎉 Success!

Once deployed, your YourMove platform will be accessible at your chosen URL. Share the link with your medical team and start revolutionizing autism therapy with AI-powered VR!

---

**Need help?** Open an issue on GitHub or contact the development team.
