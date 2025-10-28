$env:HTTP_PROXY="http://127.0.0.1:9090"
$env:HTTPS_PROXY="http://127.0.0.1:9090"
$env:NODE_TLS_REJECT_UNAUTHORIZED="0"

code $args
