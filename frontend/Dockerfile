# --- Frontend (React + Vite) ---
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

# Serve the frontend using vite preview (or nginx later)
EXPOSE 5173
CMD ["npm", "run", "preview", "--", "--host"]
