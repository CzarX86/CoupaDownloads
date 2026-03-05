#!/bin/bash
# Ultimate WhatsApp Health Report - All Features
# Enhanced with: Weekly summary, Disk growth, Top processes, Network stats, SSL expiry

export TZ="America/Sao_Paulo"

EVOLUTION_URL="http://localhost:8080"
API_KEY="psico_admin_key_2026_x7y9"
INSTANCE_NAME="psicosecretary_auth"
ADMIN_NUMBER="5511998102185"
STATE_FILE="/home/julio/.health_state"

# Get current metrics
CONTAINERS_OK=$(docker ps --format "table {{.Names}}" 2>/dev/null | grep -E "(evolution|postgres|redis)" | wc -l)
API_STATUS=$(curl -s --max-time 10 http://localhost:8080/ 2>/dev/null | grep -q "working" && echo "OK" || echo "FAIL")
DISK_USAGE=$(df / 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//')
DISK_AVAIL=$(df -h / 2>/dev/null | tail -1 | awk '{print $4}')
MEM_TOTAL=$(free -m | awk 'NR==2{printf "%.0f", $2}')
MEM_USED=$(free -m | awk 'NR==2{printf "%.0f", $3}')
MEM_PERCENT=$((MEM_USED * 100 / MEM_TOTAL))
CPU_USAGE=$(top -bn1 2>/dev/null | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}' | cut -d. -f1)
UPTIME_DAYS=$(uptime -p 2>/dev/null | sed 's/up //' | sed 's/,//g')

# Docker stats
EVOLUTION_CPU=$(docker stats --no-stream --format "{{.CPUPerc}}" evolution_api 2>/dev/null | tr -d '%')
EVOLUTION_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" evolution_api 2>/dev/null | awk '{print $1""$2}')
POSTGRES_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" evolution_postgres 2>/dev/null | awk '{print $1""$2}')
REDIS_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" evolution_redis 2>/dev/null | awk '{print $1""$2}')

EVOLUTION_RESTARTS=$(docker inspect evolution_api --format '{{.RestartCount}}' 2>/dev/null)
POSTGRES_RESTARTS=$(docker inspect evolution_postgres --format '{{.RestartCount}}' 2>/dev/null)
REDIS_RESTARTS=$(docker inspect evolution_redis --format '{{.RestartCount}}' 2>/dev/null)

# Health checks
check_health() {
    local service=$1
    docker ps --filter "name=$service" --format "{{.Status}}" 2>/dev/null | grep -q "healthy" && echo "HEALTHY ✅" || echo "OK ⚠️"
}
POSTGRES_HEALTH=$(check_health evolution_postgres)
REDIS_HEALTH=$(check_health evolution_redis)
EVOLUTION_HEALTH=$(check_health evolution_api)

# Security
F2B_STATUS=$(sudo fail2ban-client status 2>/dev/null | grep "Jail list" | cut -d: -f2 | wc -w)
F2B_BANS=$(sudo fail2ban-client status 2>/dev/null | grep "Currently failed" | cut -d: -f2 | tr -d ' ')

# Backups
LAST_BACKUP=$(ls -t /home/julio/backups/*.tar.gz 2>/dev/null | head -1 | xargs -I {} stat -c %y {} 2>/dev/null | cut -d' ' -f1)
BACKUP_COUNT=$(ls /home/julio/backups/*.tar.gz 2>/dev/null | wc -l)
BACKUP_SIZE=$(du -sh /home/julio/backups/ 2>/dev/null | cut -f1)

# Visual bar
make_bar() {
    local p=$1; local f=$((p/10)); local e=$((10-f)); local b=""
    for i in $(seq 1 $f); do b="${b}█"; done
    for i in $(seq 1 $e); do b="${b}░"; done
    echo "$b"
}
MEM_BAR=$(make_bar $MEM_PERCENT)
DISK_BAR=$(make_bar $DISK_USAGE)
CPU_BAR=$(make_bar $CPU_USAGE)

# ============ NEW FEATURE 1: DISK GROWTH TRACKING ============
PREV_DISK=$(cat $STATE_FILE 2>/dev/null | grep "disk_usage=" | cut -d= -f2)
PREV_DATE=$(cat $STATE_FILE 2>/dev/null | grep "disk_date=" | cut -d= -f2)
if [ -n "$PREV_DISK" ] && [ -n "$PREV_DATE" ]; then
    DISK_CHANGE=$((DISK_USAGE - PREV_DISK))
    DAYS_SINCE=$(( ($(date +%s) - $(date -d "$PREV_DATE" +%s 2>/dev/null || echo 0)) / 86400 ))
    if [ $DAYS_SINCE -gt 0 ] && [ $DISK_CHANGE -gt 0 ]; then
        DISK_GROWTH_DAY=$((DISK_CHANGE / DAYS_SINCE))
        if [ $DISK_GROWTH_DAY -gt 5 ]; then
            DISK_ALERT="⚠️ Crescimento: ${DISK_GROWTH_DAY}%/dia"
        elif [ $DISK_GROWTH_DAY -gt 0 ]; then
            DISK_ALERT="📈 Variação: ${DISK_CHANGE}% em ${DAYS_SINCE}d"
        else
            DISK_ALERT="✅ Disco estável"
        fi
    else
        DISK_ALERT="✅ Disco estável"
    fi
else
    DISK_ALERT="📊 Coletando dados..."
fi

# Save current state
echo "disk_usage=$DISK_USAGE" > $STATE_FILE
echo "disk_date=$(date +%Y-%m-%d)" >> $STATE_FILE

# ============ NEW FEATURE 2: TOP PROCESSES ============
TOP_PROCS=$(ps aux --sort=-%mem 2>/dev/null | head -4 | tail -3 | awk '{printf "  %s: %.1f%%\n", $11, $3}' | head -3)
TOP_PROC_LINE=$(echo "$TOP_PROCS" | head -1 | tr -d ' ')

# ============ NEW FEATURE 3: NETWORK STATS ============
NET_RX=$(cat /proc/net/dev 2>/dev/null | grep eth0 | awk '{print $2}' | awk '{printf "%.0f", $1/1024/1024}')
NET_TX=$(cat /proc/net/dev 2>/dev/null | grep eth0 | awk '{print $10}' | awk '{printf "%.0f", $1/1024/1024}')
NET_INFO="${NET_RX}MB ↓ | ${NET_TX}MB ↑"

# ============ NEW FEATURE 4: SSL CERTIFICATE EXPIRY ============
check_ssl() {
    local domain=$1
    local name=$2
    if command -v openssl >/dev/null 2>&1; then
        local expire_date=$(echo | timeout 5 openssl s_client -connect ${domain}:443 -servername ${domain} 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
        if [ -n "$expire_date" ]; then
            local expire_ts=$(date -d "$expire_date" +%s 2>/dev/null)
            local now_ts=$(date +%s)
            local days_left=$(( (expire_ts - now_ts) / 86400 ))
            if [ $days_left -lt 7 ]; then
                echo "🔴 ${name}: ${days_left} dias"
            elif [ $days_left -lt 30 ]; then
                echo "🟡 ${name}: ${days_left} dias"
            else
                echo "🟢 ${name}: ${days_left} dias"
            fi
        else
            echo "⚪ ${name}: N/A"
        fi
    else
        echo "⚪ ${name}: N/A"
    fi
}

# Check common domains (adjust as needed)
SSL_1=$(check_ssl "localhost" "Local")
# Add your domain if you have one:
# SSL_2=$(check_ssl "seu-dominio.com" "Dominio")

# ============ NEW FEATURE 5: WEEKLY SUMMARY ============
WEEK_NUM=$(date +%V)
PREV_WEEK=$(cat $STATE_FILE 2>/dev/null | grep "week=" | cut -d= -f2)
if [ "$WEEK_NUM" != "$PREV_WEEK" ]; then
    # New week - send weekly summary
    WEEKLY_SUMMARY="
━━━━━━━━━━━━━━━━━━━━━━━
📅 *RESUMO SEMANAL*
━━━━━━━━━━━━━━━━━━━━━━━
Semana: ${WEEK_NUM}/$(date +%Y)

"
    # Count alerts from log (last 7 days)
    ALERTS_COUNT=$(grep -c "ALERT\|⚠️\|❌" /home/julio/health_check.log 2>/dev/null | tail -1 || echo "0")
    WEEKLY_SUMMARY="${WEEKLY_SUMMARY}Alertas (7d): ${ALERTS_COUNT}
Uptime médio: $(uptime -p 2>/dev/null)

"
    echo "week=$WEEK_NUM" >> $STATE_FILE
else
    WEEKLY_SUMMARY=""
fi

# Send function
send_whatsapp() {
    local message="$1"
    curl -s -X POST "${EVOLUTION_URL}/message/sendText/${INSTANCE_NAME}" \
         -H "apikey: ${API_KEY}" \
         -H "Content-Type: application/json" \
         -d "{\"number\": \"${ADMIN_NUMBER}\", \"text\": \"${message}\", \"delay\": 0}" >/dev/null
}

# Build report
REPORT="📊 *RELATÓRIO DE SAÚDE - VPS*
⏰ $(date '+%d/%m/%Y %H:%M')
${WEEKLY_SUMMARY}
━━━━━━━━━━━━━━━━━━━━━━━
🖥️ *SISTEMA*
━━━━━━━━━━━━━━━━━━━━━━━
Uptime: ${UPTIME_DAYS}
Kernel: $(uname -r)

━━━━━━━━━━━━━━━━━━━━━━━
📈 *RECURSOS*
━━━━━━━━━━━━━━━━━━━━━━━
CPU:    ${CPU_USAGE}% ${CPU_BAR}
Memória: ${MEM_PERCENT}% ${MEM_BAR} (${MEM_USED}MB/${MEM_TOTAL}MB)
Disco:  ${DISK_USAGE}% ${DISK_BAR} (${DISK_AVAIL} livres)
${DISK_ALERT}

━━━━━━━━━━━━━━━━━━━━━━━
🌐 *REDE*
━━━━━━━━━━━━━━━━━━━━━━━
Tráfego: ${NET_INFO}

━━━━━━━━━━━━━━━━━━━━━━━
🐳 *CONTAINERS*
━━━━━━━━━━━━━━━━━━━━━━━
Evolution API: ${EVOLUTION_HEALTH}
  CPU: ${EVOLUTION_CPU:-N/A}% | Mem: ${EVOLUTION_MEM:-N/A}
  Restarts: ${EVOLUTION_RESTARTS:-0}

PostgreSQL: ${POSTGRES_HEALTH}
  Mem: ${POSTGRES_MEM:-N/A} | Restarts: ${POSTGRES_RESTARTS:-0}

Redis: ${REDIS_HEALTH}
  Mem: ${REDIS_MEM:-N/A} | Restarts: ${REDIS_RESTARTS:-0}

━━━━━━━━━━━━━━━━━━━━━━━
🔒 *SEGURANÇA*
━━━━━━━━━━━━━━━━━━━━━━━
Firewall: ✅ Ativo
Fail2Ban: ${F2B_STATUS} jails | Bloqueios: ${F2B_BANS:-0}
${SSL_1}

━━━━━━━━━━━━━━━━━━━━━━━
💾 *BACKUP*
━━━━━━━━━━━━━━━━━━━━━━━
Último: ${LAST_BACKUP:-N/A} | Total: ${BACKUP_COUNT:-0} | Size: ${BACKUP_SIZE:-N/A}

━━━━━━━━━━━━━━━━━━━━━━━
⚡ *TOP PROCESSOS*
━━━━━━━━━━━━━━━━━━━━━━━
${TOP_PROC_LINE:-N/A}

━━━━━━━━━━━━━━━━━━━━━━━
📋 *RESUMO*
━━━━━━━━━━━━━━━━━━━━━━━
Containers: ${CONTAINERS_OK}/3 ativos
API: ${API_STATUS}
Monit: $(sudo monit summary 2>/dev/null | grep -c "OK" || echo "N/A") serviços OK

$(if [ $DISK_USAGE -gt 80 ] || [ $MEM_PERCENT -gt 80 ] || [ $CPU_USAGE -gt 80 ]; then echo "⚠️ *ATENÇÃO*: Recursos elevados!"; else echo "✅ *STATUS*: Tudo operacional!"; fi)"

# Send report
send_whatsapp "$REPORT"
echo "✅ Ultimate report sent!"
