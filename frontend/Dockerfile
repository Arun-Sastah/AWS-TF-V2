# Step 1: Use an Nginx image to serve the React app
FROM nginx:alpine

# Step 2: Copy the build files into the Nginx container
COPY dist/ /usr/share/nginx/html

# Step 3: Expose port 80
EXPOSE 80

# Step 4: Run Nginx
CMD ["nginx", "-g", "daemon off;"]
