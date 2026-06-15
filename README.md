- Starte databasen, lim inn følgende i terminalen
$env:DB_HOST="aws-0-eu-west-3.pooler.supabase.com"
$env:DB_USER="postgres.ujyagwbonavdbydvncaz"
$env:DB_PASSWORD="skriv inn passord"
-----------------------------------------------------
- Starte nettsiden, lim inn følgende i terminalen
py manage.py runserver
------------------------------------------------
- Sjekke at man har satt Anthropic key
echo $env:ANTHROPIC_API_KEY
--> Gir den tom er ingenting satt
--------------------------------
-Sette Anthropic API-key
$env:ANTHROPIC_API_KEY = "LIM INN NØKKEL INNI HER"