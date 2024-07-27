mkdir -p ~/.streamlit/

echo "\
[theme]\n\
base='light'\n\
primaryColor='#04b6ea'\n\
\n\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
" > ~/.streamlit/config.toml
