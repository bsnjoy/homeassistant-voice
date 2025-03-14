#!/bin/bash

# Check if both parameters are provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 <seed_number> <text_to_speak>"
    exit 1
fi

# Get parameters
SEED=$1
shift
TEXT="$*"  # Combine all remaining arguments as the text

# Send request to TTS server and pipe to audio player
curl -X POST "http://183.89.239.83:7861/v1/tts" \
     -H "Content-Type: application/json" \
     -d "{\"text\": \"$TEXT\", \"format\": \"wav\", \"streaming\": \"True\", \"seed\": $SEED}" \
     --output - | aplay -D plughw:CARD=MS,DEV=0 -r 44100 -c 1 -f S16_LE -t raw
