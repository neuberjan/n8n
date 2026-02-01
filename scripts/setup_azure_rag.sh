#!/bin/bash

# ============================================
# Azure RAG Chatbot - Automatisches Setup
# ============================================

set -e

# Konfiguration - BITTE ANPASSEN
RESOURCE_GROUP="rg-rag-chatbot"
LOCATION="westeurope"
SEARCH_SERVICE_NAME="search-rag-$(openssl rand -hex 4)"
INDEX_NAME="knowledge-base-index"
SKU="free"  # "free" (€0, limitiert) oder "basic" (~€70/Monat)
SUBSCRIPTION_ID="877b4866-51a1-4065-b840-7969ca6d2964"

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Azure RAG Chatbot Setup ===${NC}\n"

# 1. Prüfen ob Azure CLI installiert ist
if ! command -v az &> /dev/null; then
    echo -e "${RED}Azure CLI nicht gefunden. Bitte installieren:${NC}"
    echo "brew install azure-cli"
    exit 1
fi

# 2. Login prüfen
echo -e "${YELLOW}Prüfe Azure Login...${NC}"
if ! az account show &> /dev/null; then
    echo "Bitte einloggen..."
    az login --only-show-errors
fi

# Subscription automatisch setzen (Visual Studio Subscription)
echo -e "${YELLOW}Setze Subscription auf Visual Studio...${NC}"
az account set --subscription $SUBSCRIPTION_ID 2>/dev/null || {
    echo -e "${RED}Fehler: Subscription $SUBSCRIPTION_ID nicht gefunden.${NC}"
    echo "Verfügbare Subscriptions:"
    az account list --query "[].{Name:name, ID:id}" -o table
    exit 1
}

SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}✓ Subscription: $SUBSCRIPTION${NC}"
echo -e "${GREEN}  ID: $SUBSCRIPTION_ID${NC}\n"

# Bestätigung einholen
echo -e "${YELLOW}Folgende Ressourcen werden erstellt:${NC}"
echo "  - Resource Group: $RESOURCE_GROUP"
echo "  - Location: $LOCATION"
echo "  - Search Service SKU: $SKU"
echo ""
read -p "Fortfahren? (j/n): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[jJyY]$ ]]; then
    echo -e "${RED}Abgebrochen.${NC}"
    exit 0
fi
echo ""

# 3. Resource Group erstellen
echo -e "${YELLOW}Erstelle Resource Group...${NC}"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output none
echo -e "${GREEN}✓ Resource Group '$RESOURCE_GROUP' erstellt${NC}\n"

# 4. Azure AI Search erstellen
echo -e "${YELLOW}Erstelle Azure AI Search Service (dauert ~2 Min)...${NC}"
az search service create \
    --name $SEARCH_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku $SKU \
    --output none
echo -e "${GREEN}✓ Search Service '$SEARCH_SERVICE_NAME' erstellt (SKU: $SKU)${NC}\n"

# 5. Search Admin Key abrufen
echo -e "${YELLOW}Rufe API Keys ab...${NC}"
SEARCH_ENDPOINT="https://${SEARCH_SERVICE_NAME}.search.windows.net"
SEARCH_ADMIN_KEY=$(az search admin-key show \
    --service-name $SEARCH_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --query primaryKey -o tsv)

# 6. Vector Index erstellen
echo -e "${YELLOW}Erstelle Vector Index...${NC}"

INDEX_DEFINITION='{
  "name": "'$INDEX_NAME'",
  "fields": [
    {"name": "id", "type": "Edm.String", "key": true, "searchable": false, "filterable": true},
    {"name": "content", "type": "Edm.String", "searchable": true, "filterable": false, "sortable": false},
    {"name": "content_vector", "type": "Collection(Edm.Single)", "searchable": true, "dimensions": 1536, "vectorSearchProfile": "vector-profile"},
    {"name": "title", "type": "Edm.String", "searchable": true, "filterable": true, "sortable": true},
    {"name": "source", "type": "Edm.String", "searchable": false, "filterable": true, "sortable": false},
    {"name": "metadata", "type": "Edm.String", "searchable": false, "filterable": false}
  ],
  "vectorSearch": {
    "profiles": [
      {
        "name": "vector-profile",
        "algorithm": "vector-algorithm",
        "vectorizer": null
      }
    ],
    "algorithms": [
      {
        "name": "vector-algorithm",
        "kind": "hnsw",
        "hnswParameters": {
          "metric": "cosine",
          "m": 4,
          "efConstruction": 400,
          "efSearch": 500
        }
      }
    ]
  }
}'

curl -s -X PUT "${SEARCH_ENDPOINT}/indexes/${INDEX_NAME}?api-version=2024-07-01" \
    -H "Content-Type: application/json" \
    -H "api-key: ${SEARCH_ADMIN_KEY}" \
    -d "$INDEX_DEFINITION" > /dev/null

echo -e "${GREEN}✓ Index '$INDEX_NAME' erstellt${NC}\n"

# 7. Ausgabe der Credentials
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SETUP ABGESCHLOSSEN!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Trage diese Werte in n8n ein:${NC}\n"

echo -e "${GREEN}Azure AI Search Credentials:${NC}"
echo "  Endpoint:    $SEARCH_ENDPOINT"
echo "  API Key:     $SEARCH_ADMIN_KEY"
echo "  Index Name:  $INDEX_NAME"
echo ""

# Credentials in Datei speichern
CREDENTIALS_FILE="$(dirname "$0")/../.azure-credentials.env"
cat > "$CREDENTIALS_FILE" << EOF
# Azure AI Search Credentials
AZURE_SEARCH_ENDPOINT=$SEARCH_ENDPOINT
AZURE_SEARCH_API_KEY=$SEARCH_ADMIN_KEY
AZURE_SEARCH_INDEX_NAME=$INDEX_NAME

# Generiert am: $(date)
EOF

echo -e "${GREEN}✓ Credentials gespeichert in: .azure-credentials.env${NC}\n"

echo -e "${YELLOW}Nächste Schritte:${NC}"
echo "1. Credentials in n8n eintragen"
echo "2. Azure OpenAI Credentials konfigurieren (falls noch nicht geschehen)"
echo "3. Telegram Bot Token eintragen"
echo "4. Daten in den Vector Store laden (separater Workflow)"
