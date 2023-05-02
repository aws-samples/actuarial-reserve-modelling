#!/bin/bash -e

# Get sorted list of all input file names
SORTED_FILELIST=($(find $INPUT_DIR -type f | sort))

# Calculate number of files for this worker to process:
#   ceiling(length(SORTED_FILELIST) / NUMBER_OF_WORKERS)
BATCH_SIZE=$(((${#SORTED_FILELIST[@]} + NUMBER_OF_WORKERS - 1) / NUMBER_OF_WORKERS))

# Get list of files for this worker to process
FILES_TO_PROCESS=(${SORTED_FILELIST[@]:$((AWS_BATCH_JOB_ARRAY_INDEX * BATCH_SIZE)):$BATCH_SIZE})

# Worker output directory
WORKER_OUTPUT_DIR="${OUTPUT_DIR}/${AWS_BATCH_JOB_ID}"
mkdir -p $WORKER_OUTPUT_DIR

echo "worker $(( AWS_BATCH_JOB_ARRAY_INDEX + 1 )) of ${NUMBER_OF_WORKERS}, processing ${#FILES_TO_PROCESS[@]} files"

for input_file in ${FILES_TO_PROCESS[@]}
do
  stripped_file=${input_file%.*}
  output_file="${WORKER_OUTPUT_DIR}/$(basename ${stripped_file}.txt)"

  if [[ -f $output_file ]]
  then
    echo "output file $output_file already exists, skipping..."
    continue
  fi

  echo "processing $input_file"

  cargo run $input_file $output_file
done