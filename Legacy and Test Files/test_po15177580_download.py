#!/usr/bin/env python3
"""
Teste específico para investigar o problema de download da PO15177580
"""

import os
import time
import sys
sys.path.append('src/utils/parallel_test')
from browser import BrowserManager
from downloader import Downloader
from download_control import DownloadControlManager
from excel_processor import ExcelProcessor
from folder_hierarchy import FolderHierarchyManager
from driver_manager import DriverManager

def test_po15177580_download():
    print("🧪 Teste Específico - Download PO15177580")
    print("=" * 50)
    
    # Configurar diretório de download
    base_download_dir = os.path.expanduser("~/Downloads")
    
    coupa_downloads_dir = os.path.join(base_download_dir, "CoupaDownloads")
    temp_download_dir = os.path.join(coupa_downloads_dir, "Temp")
    
    print(f"   📂 Base directory: {base_download_dir}")
    print(f"   📂 CoupaDownloads will be created at: {coupa_downloads_dir}")
    print(f"   📂 Temporary files will be saved at: {temp_download_dir}")
    
    # Criar diretórios
    os.makedirs(temp_download_dir, exist_ok=True)
    
    # Inicializar browser
    print("\n🚀 Initializing browser...")
    browser_manager = BrowserManager()
    browser_manager.initialize_driver_with_download_dir(temp_download_dir)
    
    # Inicializar componentes
    download_control = DownloadControlManager()
    excel_processor = ExcelProcessor()
    
    # Criar tab específica para PO15177580
    print("\n📋 Testing PO15177580 download...")
    tab_handle = browser_manager.create_new_tab()
    
    if not tab_handle:
        print("   ❌ Failed to create tab")
        return
    
    print(f"   ✅ Created tab: {tab_handle}")
    
    # Criar downloader
    downloader = Downloader(browser_manager.driver, browser_manager, download_control, temp_download_dir)
    
    # Testar download da PO
    po_number = "PO15177580"
    print(f"\n🔍 Testing download for {po_number}...")
    
    try:
        # Navegar para a PO
        url = f"https://unilever.coupahost.com/order_headers/{po_number.replace('PO', '')}"
        print(f"   🌐 Navigating to: {url}")
        
        browser_manager.driver.switch_to.window(tab_handle)
        browser_manager.driver.get(url)
        
        # Aguardar carregamento
        time.sleep(5)
        
        # Verificar se a página é válida
        print("   🔍 Checking page validity...")
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Verificar se existe o elemento que indica PO válida
            order_header = browser_manager.driver.find_element(By.CSS_SELECTOR, "#order_header_requisition_header")
            if order_header:
                print("   ✅ Valid PO page detected!")
                
                # Tentar encontrar attachments
                print("   📎 Searching for attachments...")
                attachments = downloader._find_attachments()
                
                if attachments:
                    print(f"   ✅ Found {len(attachments)} attachment(s)")
                    
                    # Tentar baixar o primeiro attachment
                    attachment = attachments[0]
                    filename = downloader._extract_filename_from_element(attachment)
                    print(f"   ⬇ Attempting to download: {filename}")
                    
                    # Verificar arquivos antes do download
                    files_before = set()
                    if os.path.exists(temp_download_dir):
                        files_before = set(os.listdir(temp_download_dir))
                    print(f"   📁 Files before download: {list(files_before)}")
                    
                    # Tentar download com estratégias detalhadas
                    try:
                        print("   🔄 Trying direct click...")
                        attachment.click()
                        time.sleep(3)
                    except Exception as e:
                        print(f"   ⚠️ Direct click failed: {e}")
                        
                        try:
                            print("   🔄 Trying JavaScript click...")
                            browser_manager.driver.execute_script("arguments[0].click();", attachment)
                            time.sleep(3)
                        except Exception as e2:
                            print(f"   ⚠️ JavaScript click failed: {e2}")
                            
                            try:
                                print("   🔄 Trying scroll + click...")
                                browser_manager.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", attachment)
                                time.sleep(1)
                                attachment.click()
                                time.sleep(3)
                            except Exception as e3:
                                print(f"   ⚠️ Scroll + click failed: {e3}")
                    
                    # Verificar se arquivo foi baixado
                    print("   🔍 Checking for downloaded file...")
                    max_wait = 10
                    wait_time = 0
                    file_downloaded = False
                    
                    while wait_time < max_wait:
                        time.sleep(1)
                        wait_time += 1
                        
                        if os.path.exists(temp_download_dir):
                            files_after = set(os.listdir(temp_download_dir))
                            new_files = files_after - files_before
                            
                            if new_files:
                                print(f"   ✅ New files detected: {list(new_files)}")
                                file_downloaded = True
                                break
                            else:
                                print(f"   ⏳ Waiting... ({wait_time}/{max_wait})")
                    
                    if not file_downloaded:
                        print("   ❌ No file downloaded after 10 seconds")
                    
                else:
                    print("   ⚠️ No attachments found")
                    
            else:
                print("   ❌ Invalid PO page - no order header found")
                
        except Exception as e:
            print(f"   ❌ Error during download process: {e}")
            
    except Exception as e:
        print(f"   ❌ Navigation error: {e}")
    
    # Fechar tab e browser
    print("\n🛑 Closing browser...")
    try:
        browser_manager.driver.switch_to.window(tab_handle)
        browser_manager.driver.close()
    except:
        pass
    
    browser_manager.cleanup()
    print("✅ Test completed!")

if __name__ == "__main__":
    test_po15177580_download()
