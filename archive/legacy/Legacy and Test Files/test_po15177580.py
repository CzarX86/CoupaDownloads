#!/usr/bin/env python3
"""
Teste específico para verificar a acessibilidade da PO15177580
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

def test_po15177580():
    print("🧪 Teste Específico - PO15177580")
    print("=" * 50)
    
    # Configurar diretório de download
    base_download_dir = input("📁 Where to save CoupaDownloads folder? (Enter for default ~/Downloads): ").strip()
    if not base_download_dir:
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
    print("\n📋 Testing PO15177580...")
    tab_handle = browser_manager.create_new_tab()
    
    if not tab_handle:
        print("   ❌ Failed to create tab")
        return
    
    print(f"   ✅ Created tab: {tab_handle}")
    
    # Criar downloader
    downloader = Downloader(browser_manager.driver, browser_manager, download_control, temp_download_dir)
    
    # Testar acesso à PO
    po_number = "PO15177580"
    print(f"\n🔍 Testing access to {po_number}...")
    
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
                    for i, attachment in enumerate(attachments, 1):
                        filename = downloader._extract_filename_from_element(attachment)
                        print(f"      {i}. {filename}")
                else:
                    print("   ⚠️ No attachments found")
                    
            else:
                print("   ❌ Invalid PO page - no order header found")
                
        except Exception as e:
            print(f"   ❌ Error checking page: {e}")
            
            # Verificar se é página de erro
            try:
                error_element = browser_manager.driver.find_element(By.XPATH, "/html/body/div[2]/div/h1")
                if error_element and "Oops!" in error_element.text:
                    print("   ❌ Error page detected: 'Oops! We couldn't find what you wanted.'")
                else:
                    print("   ❌ Unknown error page")
            except:
                print("   ❌ Page structure unknown")
                
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
    test_po15177580()
