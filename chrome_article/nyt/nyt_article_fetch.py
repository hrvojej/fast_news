import pychrome
import time
import threading

def main():
   try:
       browser = pychrome.Browser(url="http://127.0.0.1:9222")
       tab = browser.new_tab()
       
       def handle_exception(msg):
           print(f"Debug: {msg}")
       
       tab.set_listener("exception", handle_exception)
       tab.start()
       
       tab.Page.enable()
       tab.Runtime.enable()
       
       url = "https://edition.cnn.com/2025/02/04/politics/cia-workforce-buyouts/index.html"
       tab.Page.navigate(url=url)
       
       time.sleep(15)
       
       clean_html_js = """
       function cleanHTML() {
           const elements = document.querySelectorAll('script, style, iframe, link, meta');
           elements.forEach(el => el.remove());
           return document.documentElement.outerHTML;
       }
       cleanHTML();
       """
       
       result = tab.Runtime.evaluate(expression=clean_html_js)
       html_content = result["result"]["value"]

       with open("cnn.html", "w", encoding="utf-8") as f:
           f.write(html_content)
           
   except Exception as e:
       print(f"Error: {e}")
   finally:
       tab.stop()
       browser.close_tab(tab)

if __name__ == "__main__":
   main()