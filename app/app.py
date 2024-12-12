import streamlit as st
import plotly.express as px
import pandas as pd
import boto3
from datetime import datetime
import json

# Fonction pour récupérer les données depuis DynamoDB
def get_data_from_dynamodb():
    # Initialisation de la ressource DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ActivitiesTable')  # Remplace par le nom de ta table DynamoDB
    
    # Effectuer la requête pour obtenir toutes les données
    response = table.scan()  # Utiliser 'scan' pour récupérer toutes les données (peut être optimisé avec un 'query')
    
    # Extraire les items de la réponse
    items = response.get('Items', [])
    
    return items

# Récupérer les données depuis DynamoDB
data = get_data_from_dynamodb()

# Convertir les données en DataFrame
df = pd.DataFrame(data)

# Vérifier si les colonnes nécessaires sont présentes
if 'startTimeLocal' in df.columns and 'duration' in df.columns:
    # Convertir la date au format datetime
    df['date'] = pd.to_datetime(df['startTimeLocal'], format='%Y-%m-%d %H:%M:%S')
    
    # Ajouter une colonne pour l'identifiant unique de semaine (par exemple: "2024-S01")
    df['semaine_unique'] = df['date'].dt.strftime('%Y-S%W')
    
    # Convertir la durée en secondes en heures
    df['durée'] = df['duration'] / 3600  # Conversion en heures

    print(df['activityType'].apply(lambda x: x['typeKey']))
    # Extraire le type de sport (par exemple "walking", "swimming") depuis la colonne 'activityType' qui est un JSON
    df['sport'] = df['activityType'].apply(lambda x: x['typeKey'])
    sports_list = df['sport'].unique()
    print(sports_list)

    # Ajouter une multiselect pour sélectionner les sports
    selected_sports = st.multiselect('Sélectionnez les sports à afficher', sports_list, default=sports_list)
    
    df_filtered = df[df['sport'].isin(selected_sports)]
    
    
    # Regrouper par semaine (semaine_unique) et calculer la somme des durées
    df_semaine = df_filtered.groupby('semaine_unique').agg({'durée': 'sum'}).reset_index()

    # Créer un graphique avec Plotly
    fig = px.bar(df_semaine, x='semaine_unique', y='durée', 
                 title="Volume d'activités par semaine",
                 labels={'semaine_unique': 'Semaine', 'durée': 'Volume (heures)'},
                 color='semaine_unique', 
                 category_orders={'semaine_unique': sorted(df_semaine['semaine_unique'].unique())})
    
    # Mettre à jour la mise en page pour réduire l'écart entre les barres
    fig.update_layout(bargap=0.1)  # Réduit l'écart entre les barres
    
    # Afficher le graphique dans Streamlit
    st.title('Volume d\'activités par semaine')
    st.plotly_chart(fig)
else:
    st.error("Les colonnes 'startTimeLocal' et 'duration' sont nécessaires dans votre table DynamoDB.")

