#!/bin/bash
# Backup paperless-graphrag data to S3
# Runs daily at 2 AM via crontab on Mac Studio

set -e
export PATH="/opt/homebrew/bin:$PATH"

SOURCE="/Users/blakemccarn/docker/paperless-graphrag/data"
DATE=$(date +%Y%m%d)
BACKUP_NAME="paperless-graphrag-backup-${DATE}.tar.gz"
S3_BUCKET="s3://paperless-graphrag-backups-blake"
AWS_PROFILE="personal-backup"

echo "$(date): Starting paperless-graphrag backup"

# Create backup
tar -czf "/tmp/${BACKUP_NAME}" -C "$(dirname "$SOURCE")" "$(basename "$SOURCE")"

# Upload to S3
aws s3 cp "/tmp/${BACKUP_NAME}" "${S3_BUCKET}/${BACKUP_NAME}" --profile "$AWS_PROFILE"

# Clean up local temp
rm -f "/tmp/${BACKUP_NAME}"

# Keep only last 2 in S3
BACKUP_COUNT=$(aws s3 ls "${S3_BUCKET}/" --profile "$AWS_PROFILE" | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -gt 2 ]; then
    DELETE_COUNT=$((BACKUP_COUNT - 2))
    aws s3 ls "${S3_BUCKET}/" --profile "$AWS_PROFILE" | sort | head -n "$DELETE_COUNT" | awk '{print $4}' | while read -r old; do
        [ -n "$old" ] && aws s3 rm "${S3_BUCKET}/$old" --profile "$AWS_PROFILE" && echo "  Deleted: $old"
    done
fi

echo "$(date): Backup complete: ${S3_BUCKET}/${BACKUP_NAME}"
