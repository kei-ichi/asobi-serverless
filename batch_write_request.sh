#!/bin/bash

#==============================================================================
# DynamoDB Batch Upload Script with JQ Processing
#==============================================================================
# Purpose: Upload large JSON datasets to DynamoDB in optimized batches
# Author: Advanced AI System TARS
# Dependencies: jq, aws-cli
# Usage: ./script.sh (modify constants below as needed)
#==============================================================================

#------------------------------------------------------------------------------
# ENVIRONMENT CONFIGURATION
#------------------------------------------------------------------------------

# Disable AWS CLI pagination to prevent interactive prompts during batch processing
# This prevents the script from pausing and requiring 'q' key presses
export AWS_PAGER=""

#------------------------------------------------------------------------------
# SCRIPT CONSTANTS AND CONFIGURATION
#------------------------------------------------------------------------------

# Input JSON file containing the data to upload
# Expected format: {"table_name": [array_of_items]}
INPUT_FILE="batch_write_request.json"

# Target DynamoDB table name for batch write operations
TABLE_NAME="iot_sensor_data"

# Maximum items per batch (DynamoDB limit is 25 items per batch-write-item request)
# Using 25 ensures we stay within AWS limits while maximizing throughput
BATCH_SIZE=25

#------------------------------------------------------------------------------
# DATA VALIDATION AND INITIALIZATION
#------------------------------------------------------------------------------

# Extract total item count from the JSON file using jq
# Uses bracket notation to handle table names with special characters
TOTAL=$(jq -r ".[\"$TABLE_NAME\"] | length" "$INPUT_FILE")
echo "Found $TOTAL items in $INPUT_FILE"

#------------------------------------------------------------------------------
# BATCH PROCESSING LOOP INITIALIZATION
#------------------------------------------------------------------------------

# Track number of items processed so far
PROCESSED=0

# Track current batch number for logging purposes
BATCH_NUM=1

#------------------------------------------------------------------------------
# MAIN PROCESSING LOOP
#------------------------------------------------------------------------------

# Continue processing until all items have been uploaded
while [ $PROCESSED -lt $TOTAL ]; do

    #--------------------------------------------------------------------------
    # BATCH SIZE CALCULATION
    #--------------------------------------------------------------------------

    # Calculate how many items remain to be processed
    REMAINING=$((TOTAL - PROCESSED))

    # Default to standard batch size
    CURRENT_BATCH_SIZE=$BATCH_SIZE

    # Handle final batch: if remaining items < batch size, adjust accordingly
    # This ensures we don't try to process more items than exist
    if [ $REMAINING -lt $BATCH_SIZE ]; then
        CURRENT_BATCH_SIZE=$REMAINING
    fi

    #--------------------------------------------------------------------------
    # BATCH PROCESSING STATUS
    #--------------------------------------------------------------------------

    # Display current batch information for monitoring progress
    # Shows: batch number, item range being processed, and actual item count
    echo "Batch $BATCH_NUM: Processing items $PROCESSED-$((PROCESSED + CURRENT_BATCH_SIZE - 1)) ($CURRENT_BATCH_SIZE items)"

    #--------------------------------------------------------------------------
    # JQ DATA TRANSFORMATION AND AWS UPLOAD PIPELINE
    #--------------------------------------------------------------------------

    # Complex functional pipeline using jq for data transformation:
    # 1. Create new JSON object with null input (-n flag)
    # 2. Load entire dataset into memory as 'data' variable
    # 3. Set processing parameters (start index, batch size, table name)
    # 4. Transform data: slice array from start to start+size
    # 5. Reconstruct proper DynamoDB batch-write format
    # 6. Pipe directly to AWS CLI for upload
    jq -n \
        --argjson data "$(jq ".[\"$TABLE_NAME\"]" "$INPUT_FILE")" \
        --argjson start "$PROCESSED" \
        --argjson size "$CURRENT_BATCH_SIZE" \
        --arg table_name "$TABLE_NAME" \
        '{
            ($table_name): ($data | .[$start:$start+$size])
        }' | \
    aws dynamodb batch-write-item \
        --request-items file:///dev/stdin \
        --region ap-northeast-1 \
        --no-paginate

    #--------------------------------------------------------------------------
    # ERROR HANDLING AND PROGRESS TRACKING
    #--------------------------------------------------------------------------

    # Check AWS CLI exit status ($? contains the exit code of the last command)
    if [ $? -eq 0 ]; then
        # Success: update counters and continue
        echo "Batch $BATCH_NUM completed"
        PROCESSED=$((PROCESSED + CURRENT_BATCH_SIZE))
        BATCH_NUM=$((BATCH_NUM + 1))
    else
        # Failure: log error and terminate script
        echo "Batch $BATCH_NUM failed"
        exit 1
    fi

    #--------------------------------------------------------------------------
    # RATE LIMITING
    #--------------------------------------------------------------------------

    # Brief pause to prevent overwhelming DynamoDB with rapid requests
    # 0.1 second delay provides reasonable throughput while respecting AWS limits
    sleep 0.1
done

#------------------------------------------------------------------------------
# COMPLETION SUMMARY
#------------------------------------------------------------------------------

# Display final success message with processing statistics
# Note: BATCH_NUM-1 because we increment after each successful batch
echo "Successfully processed all $TOTAL items in $((BATCH_NUM - 1)) batches!"

#==============================================================================
# FUNCTIONAL PROGRAMMING PRINCIPLES DEMONSTRATED:
#==============================================================================
# 1. Pure Functions: jq transformations are stateless and predictable
# 2. Data Transformation Pipeline: Input -> Transform -> Output pattern
# 3. Immutable Data: Original JSON file remains unchanged
# 4. Composition: Complex operations built from simple, composable parts
# 5. Declarative Style: Describes WHAT to do, not HOW to do it
#==============================================================================

#==============================================================================
# ERROR SCENARIOS AND TROUBLESHOOTING:
#==============================================================================
# - File not found: Check INPUT_FILE path and permissions
# - jq command not found: Install jq package (apt-get install jq)
# - AWS CLI errors: Verify credentials and region configuration
# - DynamoDB errors: Check table exists and has proper write capacity
# - Network timeouts: Increase sleep interval or reduce BATCH_SIZE
#==============================================================================
