#!/bin/bash
# Wait for Elasticsearch to start up before doing anything.
sleep 20

# Apply the mapping update
curl -X PUT "localhost:9200/products/_mapping" -H 'Content-Type: application/json' -d '{
  "properties": {
    "title": {
      "type": "text",
      "fielddata": true
    }
  }
}'