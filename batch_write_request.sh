#!/bin/bash

#==============================================================================
# DynamoDB Batch Upload - Corrected File-Based Processing
#==============================================================================

export AWS_PAGER=""

INPUT_FILE="batch_write_request.json"
TABLE_NAME="iot_sensor_data"
BATCH_SIZE=25

echo "=== Processing $INPUT_FILE ==="

# Get total count for progress tracking
TOTAL=$(jq -r ".[\"$TABLE_NAME\"] | length" "$INPUT_FILE")
echo "Found $TOTAL items to process"

# Calculate total batches needed
TOTAL_BATCHES=$(( (TOTAL + BATCH_SIZE - 1) / BATCH_SIZE ))
echo "Will create $TOTAL_BATCHES batches of size $BATCH_SIZE"

#------------------------------------------------------------------------------
# CORRECTED: Simple loop-based batch processing
#------------------------------------------------------------------------------

for ((batch=0; batch<TOTAL_BATCHES; batch++)); do
    START_IDX=$((batch * BATCH_SIZE))
    BATCH_NUM=$((batch + 1))

    echo -n "Batch $BATCH_NUM/$TOTAL_BATCHES: "

    # Create batch using standard jq array slicing
    jq \
        --argjson start "$START_IDX" \
        --argjson size "$BATCH_SIZE" \
        --arg table_name "$TABLE_NAME" \
        '{
            ($table_name): (.[$table_name] | .[$start:$start+$size])
        }' "$INPUT_FILE" > "temp_batch.json"

    # Check if batch file was created successfully
    if [ ! -s "temp_batch.json" ]; then
        echo "Failed to create batch file"
        exit 1
    fi

    # Upload batch
    if aws dynamodb batch-write-item \
        --request-items file://temp_batch.json \
        --region ap-northeast-1 \
        --no-paginate > /dev/null 2>&1; then

        echo "SUCCESS"
        rm "temp_batch.json"
    else
        echo "FAILED"
        echo "Batch file saved as: temp_batch_${BATCH_NUM}.json"
        mv "temp_batch.json" "temp_batch_${BATCH_NUM}.json"
        exit 1
    fi

    sleep 0.1
done

echo ""
echo "Successfully processed all $TOTAL items in $TOTAL_BATCHES batches!"
