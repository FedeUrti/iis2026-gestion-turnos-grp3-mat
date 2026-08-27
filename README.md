# Uru Turn! - Plataforma de Gestión de Turnos (Parte 1)

Proyecto de gestión distribuida de turnos utilizando arquitectura orientada a eventos con MQTT y Docker.

## Requisitos
- Docker y Docker Compose

## Ejecución del Entorno
1. Iniciar el broker MQTT (Eclipse Mosquitto):
   docker compose up -d

## Ejecución de Scripts
- Escuchar solicitudes de turnos:
  ./scripts/suscribirse-turnos.sh

- Publicar un nuevo turno:
  ./scripts/publicar-turno.sh
Plantilla de vision de moore:
https://drive.google.com/file/d/1e86nDw9qDQcqUNdyuP-YC8tFWUXKZFRY/view?usp=sharing
