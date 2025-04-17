export default {
	async fetch(request, env, ctx) {
	  const url = new URL(request.url);  
	  // 1. Redirect www.fast-news.net → fast-news.net
	  if (url.hostname === "www.fast-news.net") {
	  	url.hostname = "fast-news.net";
	  	return Response.redirect(url.toString(), 301);
	  }
	  
	  // 2. Redirect root path to homepage.html
	  if (url.hostname === "fast-news.net" && (url.pathname === "/" || url.pathname === "")) {
	  	return Response.redirect("https://fast-news.net/homepage.html", 301);
	  }
	  
	  let path = url.pathname;
		
	  
	  // Handle root requests
	  if (path === "/" || path === "") {
		path = "/homepage.html";
	  }
	  
	  // Remove leading slash for R2 key
	  const key = path.startsWith("/") ? path.substring(1) : path;
	  
	  // Try to get the object from R2
	  const object = await env.STATIC_BUCKET.get(key);
	  
	  if (object === null) {
		// If the file doesn't exist, try adding .html
		const htmlKey = key.endsWith(".html") ? key : `${key}.html`;
		const htmlObject = await env.STATIC_BUCKET.get(htmlKey);
		
		if (htmlObject === null) {
		  // Try to fetch a custom 404 page
		  const notFoundObject = await env.STATIC_BUCKET.get("404.html");
		  
		  if (notFoundObject === null) {
			return new Response("Not Found", { status: 404 });
		  } else {
			const headers = new Headers();
			headers.set("content-type", "text/html");
			// No caching for error pages
			headers.set("Cache-Control", "no-cache, no-store, must-revalidate");
			// Add security headers
			headers.set("X-Content-Type-Options", "nosniff");
			headers.set("X-Frame-Options", "DENY");
			headers.set("X-XSS-Protection", "1; mode=block");
			headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
			
			return new Response(notFoundObject.body, { 
			  status: 404,
			  headers 
			});
		  }
		}
		
		const headers = new Headers();
		headers.set("content-type", "text/html");
		// Short caching for HTML files that change frequently
		headers.set("Cache-Control", "public, max-age=900"); // Cache for 15 minutes
		// Add security headers
		headers.set("X-Content-Type-Options", "nosniff");
		headers.set("X-Frame-Options", "DENY");
		headers.set("X-XSS-Protection", "1; mode=block");
		headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
		
		return new Response(htmlObject.body, { headers });
	  }
	  
	  // Determine content type based on file extension
	  const contentType = getContentType(key);
	  const headers = new Headers();
	  headers.set("content-type", contentType);
	  
	  // Add caching headers - different cache times based on file type
	  if (contentType === "text/html") {
		// Short caching for HTML files that change frequently
		headers.set("Cache-Control", "public, max-age=900"); // Cache for 15 minutes
	  } else if (contentType.startsWith("image/") || contentType === "text/css" || contentType === "application/javascript") {
		headers.set("Cache-Control", "public, max-age=604800"); // Cache for 7 days
	  } else {
		headers.set("Cache-Control", "public, max-age=86400"); // Cache for 1 day
	  }
	  
	  // Add security headers
	  headers.set("X-Content-Type-Options", "nosniff");
	  headers.set("X-Frame-Options", "DENY");
	  headers.set("X-XSS-Protection", "1; mode=block");
	  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
	  
	  return new Response(object.body, { headers });
	}
  };
  
  function getContentType(filename) {
	const ext = filename.split('.').pop().toLowerCase();
	const types = {
	  // Document types
	  'html': 'text/html',
	  'css': 'text/css',
	  'js': 'application/javascript',
	  'json': 'application/json',
	  'xml': 'application/xml',
	  'pdf': 'application/pdf',
	  'txt': 'text/plain',
	  
	  // Image types
	  'jpg': 'image/jpeg',
	  'jpeg': 'image/jpeg',
	  'png': 'image/png',
	  'gif': 'image/gif',
	  'svg': 'image/svg+xml',
	  'ico': 'image/x-icon',
	  'webp': 'image/webp',
	  
	  // Video types
	  'webm': 'video/webm',
	  'mp4': 'video/mp4',
	  'mov': 'video/quicktime',
	  'avi': 'video/x-msvideo',
	  
	  // Audio types
	  'mp3': 'audio/mpeg',
	  'wav': 'audio/wav',
	  'ogg': 'audio/ogg',
	  
	  // Font types
	  'woff': 'font/woff',
	  'woff2': 'font/woff2',
	  'ttf': 'font/ttf',
	  'otf': 'font/otf',
	  'eot': 'application/vnd.ms-fontobject',
	  
	  // Archive types
	  'zip': 'application/zip',
	  'rar': 'application/x-rar-compressed'
	};
	
	return types[ext] || 'application/octet-stream';
  }