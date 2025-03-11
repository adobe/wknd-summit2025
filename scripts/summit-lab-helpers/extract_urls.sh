#!/bin/sh

# Help function
show_help() {
    echo "Usage: This script extracts 'id' and 'baseURL' fields from JSON input and creates a CSV file."
    echo
    echo "The script expects JSON input from stdin. You can use it with curl like this:"
    echo "  curl -s https://spacecat.experiencecloud.live/api/v1/organizations/d488fc90-d009-412c-82a1-70b338b1869c/sites/ -H "Authorization: Bearer $ASO_TOKEN" | ./extract_urls.sh"
    echo
    echo "Example with sample JSON data:"
    echo "  echo '[{\"id\":\"123\",\"baseURL\":\"https://example.com\"}]' | ./extract_urls.sh"
    echo
    echo "Options:"
    echo "  -h    Show this help message"
}

# Handle command line arguments
case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
esac

# Check if there's input on stdin
if [ -t 0 ]; then
    echo "Error: No input provided"
    echo "This script expects JSON input from stdin."
    echo "Use -h for usage information"
    exit 1
fi

# Check if jq is installed
if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is not installed. Please install it first."
    exit 1
fi

# Create CSV header
echo "id,baseURL" > output.csv

# Process JSON from stdin and append to CSV
jq -r '.[] | [.id, .baseURL] | @csv' >> output.csv

echo "CSV file has been created as output.csv" 