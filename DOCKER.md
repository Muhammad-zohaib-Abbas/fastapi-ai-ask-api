# Docker deployment

The API image does not include PostgreSQL. It connects to the database in
`DATABASE_URL`, which must be reachable from the Docker host.

## Supabase setup

1. Create a Supabase project.
2. In **Database → Extensions**, enable the `vector` extension.
3. In **Connect**, copy the **Session pooler** connection string. Supabase's
   direct connection is IPv6-only on the Free plan; the session pooler is the
   IPv4-compatible option for common hosts and local Windows machines.
4. Put the connection string in the server's `.env` as `DATABASE_URL` and add
   `?sslmode=require` (or `&sslmode=require` if the string already has query
   parameters). URL-encode reserved characters in the database password.

The migrations create the base tables if the database is empty, then add the
document-to-chunk relationship. They do not copy rows from another database.

## Prepare the server

1. Copy or clone this project onto the server.
2. Create a server-side `.env` file using `.env.example` as a guide. Set the
   production `GEMINI_API_KEY` and `DATABASE_URL`. Keep `.env` out of source
   control.
3. Make sure the database accepts connections from the server/container.

## Apply the migration and start the API

Run these commands from the project directory:

```sh
docker compose build
docker compose --profile migration run --rm migrate
docker compose up -d api
```

Check the container and logs:

```sh
docker compose ps
docker compose logs -f api
```

The API listens on port `8000` by default. Set `API_PORT` in `.env` to change
the host port. The root health endpoint is `/`; interactive API documentation
is at `/docs`.

## Free live URL with Render

1. Push the project to GitHub, including `render.yaml`.
2. In Render, choose **New → Blueprint** and connect the GitHub repository.
   Render reads `render.yaml` and creates the free Docker web service.
3. Enter `GEMINI_API_KEY` and `DATABASE_URL` when Render asks for the values.
4. Before asking questions, run `python -m scripts.migrate_db` from your local
   project with `DATABASE_URL` pointing at Supabase. Ingest your PDF the same
   way with `python -m scripts.ingest_pdf "path/to/file.pdf"`.
5. Open the service's `onrender.com` URL, then visit `/docs` to use the API.

## Deploying a later update

After updating the project files on the server, run:

```sh
docker compose build
docker compose --profile migration run --rm migrate
docker compose up -d api
```

The migration runner applies SQL files from `migrations/` in filename order.
