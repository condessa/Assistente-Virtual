#!/bin/bash
# ==========================================
# 💾 BACKUP VERSÃO PT — Assistente Virtual
# ==========================================

DIR_PROJETO=~/Programas/Assistente\ Virtual
BACKUP_DIR=~/Backups/AssistenteVirtual
DATA=$(date +"%Y-%m-%d_%H-%M")
BACKUP_NOME="AssistenteVirtual_PT_${DATA}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NOME}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "💾 BACKUP VERSÃO PT — Assistente Virtual"
echo "=========================================="
echo ""

# Criar pasta de backups
mkdir -p "$BACKUP_DIR"

# Copiar projeto completo
echo "📂 A copiar projeto para:"
echo "   $BACKUP_PATH"
echo ""

cp -r "$DIR_PROJETO" "$BACKUP_PATH"

# Copiar também o config do utilizador
CONFIG_DIR=~/.config/assistente-virtual
if [ -d "$CONFIG_DIR" ]; then
    cp -r "$CONFIG_DIR" "${BACKUP_PATH}/_config_utilizador"
    echo "⚙️  Config do utilizador incluída"
fi

echo ""
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}✅ Backup concluído!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo "📦 Localização: $BACKUP_PATH"
echo "📏 Tamanho: $(du -sh "$BACKUP_PATH" | cut -f1)"
echo ""
echo "Para restaurar esta versão:"
echo "  cp -r \"$BACKUP_PATH\" \"$DIR_PROJETO\""
echo ""
