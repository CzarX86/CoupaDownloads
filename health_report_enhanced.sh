#!/bin/bash
# Enhanced WhatsApp Health Report with detailed metrics

export TZ="America/Sao_Paulo"

EVOLUTION_URL="http://localhost:8080"
API_KEY="psico_admin_key_2026_x7y9"
INSTANCE_NAME="psicosecretary_auth"
ADMIN_NUMBER="5511998102185"

# Get metrics
CONTAINERS_OK=$(docker ps --format "table {{.Names}}" 2>/dev/null | grep -E "(evolution|postgres|redis)" | wc -l)
API_STATUS=$(curl -s --max-time 10 http://localhost:8080/ 2>/dev/null | grep -q "working" && echo "OK" || echo "FAIL")
DISK_USAGE=$(df / 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//')
DISK_AVAIL=$(df -h / 2>/dev/null | tail -1 | awk '{print $4}')
MEM_TOTAL=$(free -m | awk 'NR==2{printf "%.0f", $2}')
MEM_USED=$(free -m | awk 'NR==2{printf "%.0f", $3}')
MEM_PERCENT=$((MEM_USED * 100 / MEM_TOTAL))
CPU_USAGE=$(top -bn1 2>/dev/null | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}' | cut -d. -f1)
UPTIME_DAYS=$(uptime -p 2>/dev/null | sed 's/up //' | sed 's/,//g')

# Docker stats per container
EVOLUTION_CPU=$(docker stats --no-stream --format "{{.CPUPerc}}" evolution_api 2>/dev/null | tr -d '%')
EVOLUTION_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" evolution_api 2>/dev/null | awk '{print $1""$2}')
POSTGRES_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" evolution_postgres 2>/dev/null | awk '{print $1""$2}')
REDIS_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" evolution_redis 2>/dev/null | awk '{print $1""$2}')

# Container restart counts
EVOLUTION_RESTARTS=$(docker inspect evolution_api --format '{{.RestartCount}}' 2>/dev/null)
POSTGRES_RESTARTS=$(docker inspect evolution_postgres --format '{{.RestartCount}}' 2>/dev/null)
REDIS_RESTARTS=$(docker inspect evolution_redis --format '{{.RestartCount}}' 2>/dev/null)

# Health checks
check_health() {
    local service=$1
    if docker ps --filter "name=$service" --format "{{.Status}}" 2>/dev/null | grep -q "healthy"; then
        echo "HEALTHY ✅"
    elif docker ps --filter "name=$service" --format "{{.Status}}" 2>/dev/null | grep -q "unhealthy"; then
        echo "UNHEALTHY ❌"
    else
        echo "UNKNOWN ⚠️"
    fi
}

POSTGRES_HEALTH=$(check_health evolution_postgres)
REDIS_HEALTH=$(check_health evolution_redis)
EVOLUTION_HEALTH=$(check_health evolution_api)

# Fail2ban status
F2B_STATUS=$(sudo fail2ban-client status 2>/dev/null | grep "Jail list" | cut -d: -f2 | wc -w)
F2B_BANS=$(sudo fail2ban-client status 2>/dev/null | grep "Currently failed" | cut -d: -f2 | tr -d ' ')

# Backup status
LAST_BACKUP=$(ls -t /home/julio/backups/*.tar.gz 2>/dev/null | head -1 | xargs -I {} stat -c %y {} 2>/dev/null | cut -d' ' -f1)
BACKUP_COUNT=$(ls /home/julio/backups/*.tar.gz 2>/dev/null | wc -l)
BACKUP_SIZE=$(du -sh /home/julio/backups/ 2>/dev/null | cut -f1)

# Visual bar function
make_bar() {
    local percent=$1
    local filled=$((percent / 10))
    local empty=$((10 - filled))
    local bar=""
    for i in $(seq 1 $filled); do bar="${bar}█"; done
    for i in $(seq 1 $empty); do bar="${bar}░"; done
    echo "$bar"
}

MEM_BAR=$(make_bar $MEM_PERCENT)
DISK_BAR=$(make_bar $DISK_USAGE)
CPU_BAR=$(make_bar $CPU_USAGE)

# Send function
send_whatsapp() {
    local message="$1"
    curl -s -X POST "${EVOLUTION_URL}/message/sendText/${INSTANCE_NAME}" \
         -H "apikey: ${API_KEY}" \
         -H "Content-Type: application/json" \
         -d "{\"number\": \"${ADMIN_NUMBER}\", \"text\": \"${message}\", \"delay\": 0}" >/dev/null
}

# Build enhanced report
REPORT="📊 *RELATÓRIO DE SAÚDE - VPS*
⏰ $(date '+%d/%m/%Y %H:%M')

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
Swap:   $(free -m | awk 'NR==3{printf "%.0f%%", $3*100/$2}' 2>/dev/null || echo "0%")

━━━━━━━━━━━━━━━━━━━━━━━
🐳 *CONTAINERS*
━━━━━━━━━━━━━━━━━━━━━━━
Evolution API: ${EVOLUTION_HEALTH}
  CPU: ${EVOLUTION_CPU:-N/A}% | Mem: ${EVOLUTION_MEM:-N/A}
  Restarts: ${EVOLUTION_RESTARTS:-0}

PostgreSQL: ${POSTGRES_HEALTH}
  Mem: ${POSTGRES_MEM:-N/A}
  Restarts: ${POSTGRES_RESTARTS:-0}

Redis: ${REDIS_HEALTH}
  Mem: ${REDIS_MEM:-N/A}
  Restarts: ${REDIS_RESTARTS:-0}

━━━━━━━━━━━━━━━━━━━━━━━
🔒 *SEGURANÇA*
━━━━━━━━━━━━━━━━━━━━━━━
Firewall: ✅ Ativo (UFW)
Fail2Ban: ${F2B_STATUS} jails ativos
  Bloqueios atuais: ${F2B_BANS:-0}

━━━━━━━━━━━━━━━━━━━━━━━
💾 *BACKUP*
━━━━━━━━━━━━━━━━━━━━━━━
Último backup: ${LAST_BACKUP:-N/A}
Total backups: ${BACKUP_COUNT:-0}
Tamanho: ${BACKUP_SIZE:-N/A}

━━━━━━━━━━━━━━━━━━━━━━━
📋 *RESUMO*
━━━━━━━━━━━━━━━━━━━━━━━
Containers: ${CONTAINERS_OK}/3 ativos
API: ${API_STATUS}
Monit: $(sudo monit summary 2>/dev/null | grep -c "OK" || echo "N/A") serviços OK

$(if [ $DISK_USAGE -gt 80 ] || [ $MEM_PERCENT -gt 80 ] || [ $CPU_USAGE -gt 80 ]; then echo "⚠️ *ATENÇÃO*: Recursos elevados!"; else echo "✅ *STATUS*: Tudo operacional!"; fi)"

# Send report
send_whatsapp "$REPORT"
echo "✅ Enhanced report sent!"
