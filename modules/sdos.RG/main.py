import os
import re
from colorama import init, Fore
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import tkinter as tk
from tkinter import filedialog

init()


def _project_root():
    cwd = os.path.abspath(os.getcwd())
    if os.path.exists(os.path.join(cwd, "main.py")) or os.path.isdir(os.path.join(cwd, "modules")):
        return cwd

    here = os.path.abspath(os.path.dirname(__file__))
    parts = here.split(os.sep)
    lower_parts = [p.lower() for p in parts]
    if "modules" in lower_parts:
        idx = len(lower_parts) - 1 - lower_parts[::-1].index("modules")
        candidate = os.sep.join(parts[:idx]) if idx > 0 else os.sep
        if os.path.isdir(candidate):
            return candidate
    return cwd


BASE_DIR = _project_root()
CLOUD_RESULTS_DIR = os.path.join(BASE_DIR, "results", "CLOUD MANAGER")


def create_results_directory():
    os.makedirs(os.path.join(CLOUD_RESULTS_DIR, "ULP"), exist_ok=True)
    os.makedirs(os.path.join(CLOUD_RESULTS_DIR, "LOGINPASS"), exist_ok=True)
    os.makedirs(os.path.join(CLOUD_RESULTS_DIR, "DOMAIN"), exist_ok=True)
    os.makedirs(os.path.join(CLOUD_RESULTS_DIR, "formats"), exist_ok=True)
    os.makedirs(os.path.join(CLOUD_RESULTS_DIR, "cookies"), exist_ok=True)


def find_txt_files(folder_path):
    txt_files = []
    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.txt'):
                    txt_files.append(os.path.join(root, file))
        return txt_files
    except Exception as e:
        print(Fore.RED + f"Error scanning directory: {e}" + Fore.RESET)
        return []


# --- FUNÇÕES GLOBAIS DE EXTRAÇÃO (Necessárias para o Multiprocessamento) ---

def _extract_ulp_worker(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()

        pattern = re.compile(
            r'URL: (?P<url>.+)\n'
            r'Username: (?P<user>.+)\n'
            r'Password: (?P<password>.+)\n'
        )
        matches = pattern.finditer(content)
        return [f"{match.group('url')}:{match.group('user')}:{match.group('password')}" for match in matches], None
    except Exception as e:
        return None, str(e)


def _extract_login_pass_worker(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()

        pattern = re.compile(
            r'Username: (?P<user>.+)\n'
            r'Password: (?P<password>.+)\n'
        )
        matches = pattern.finditer(content)
        return [f"{match.group('user')}:{match.group('password')}" for match in matches], None
    except Exception as e:
        return None, str(e)


def _extract_domain_logins_worker(args):
    file_path, target_domain = args
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()

        pattern = re.compile(
            r'URL: (?P<url>.+)\n'
            r'Username: (?P<user>.+)\n'
            r'Password: (?P<password>.+)\n'
        )
        results = []
        for match in pattern.finditer(content):
            url = match.group('url')
            if target_domain.lower() in url.lower():
                results.append(f"{match.group('user')}:{match.group('password')}")
        return results, None
    except Exception as e:
        return None, str(e)


def _extract_cookies_worker(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()

        pattern = re.compile(
            r'([^\s]+)\t'
            r'([^\s]+)\t'
            r'([^\s]+)\t'
            r'([^\s]+)\t'
            r'([^\s]+)\t'
            r'([^\s]+)\t'
            r'([^\n]+)'
        )
        cookies = []
        for match in pattern.finditer(content):
            cookies.append(f"{match.group(1)}\t{match.group(2)}\t{match.group(3)}\t"
                         f"{match.group(4)}\t{match.group(5)}\t{match.group(6)}\t{match.group(7)}")
        return cookies, None
    except Exception as e:
        return None, str(e)


# --------------------------------------------------------------------------

def save_batch_data(data_list, output_path):
    if not data_list:
        return 0
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        existing_data = set()
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as file:
                existing_data = set(line.strip() for line in file.readlines())

        new_data = set(data_list) - existing_data
        if new_data:
            with open(output_path, 'a', encoding='utf-8') as file:
                file.write("\n".join(new_data) + "\n")
            return len(new_data)
        return 0
    except Exception as e:
        print(Fore.RED + f"Error saving data to {output_path}: {e}" + Fore.RESET)
        return 0


def classify_login(login):
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    cpf_pattern = re.compile(r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$')

    if email_pattern.match(login):
        return 'email'
    elif cpf_pattern.match(login):
        return 'cpf'
    else:
        return 'user'


def process_ulp_to_formats(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = [line.strip() for line in file.readlines() if line.strip()]

        email_pass = []
        cpf_pass = []
        user_pass = []

        for line in lines:
            parts = re.split(r':(?!//)', line)
            if len(parts) >= 3:
                login = parts[-2].strip()
                password = parts[-1].strip()

                login_type = classify_login(login)
                if login_type == 'cpf':
                    login = re.sub(r'[^0-9]', '', login)

                if login_type == 'email':
                    email_pass.append(f"{login}:{password}")
                elif login_type == 'cpf':
                    cpf_pass.append(f"{login}:{password}")
                else:
                    user_pass.append(f"{login}:{password}")

        formats_dir = os.path.join(CLOUD_RESULTS_DIR, "formats")
        os.makedirs(formats_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_saved = 0

        if email_pass:
            output_file = os.path.join(formats_dir, f"emailpass_{timestamp}.txt")
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write("\n".join(email_pass) + "\n")
            total_saved += len(email_pass)
            print(Fore.GREEN + f"Saved {len(email_pass)} email:pass combinations to {output_file}" + Fore.RESET)

        if cpf_pass:
            output_file = os.path.join(formats_dir, f"cpfpass_{timestamp}.txt")
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write("\n".join(cpf_pass) + "\n")
            total_saved += len(cpf_pass)
            print(Fore.GREEN + f"Saved {len(cpf_pass)} CPF:pass combinations to {output_file}" + Fore.RESET)

        if user_pass:
            output_file = os.path.join(formats_dir, f"userpass_{timestamp}.txt")
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write("\n".join(user_pass) + "\n")
            total_saved += len(user_pass)
            print(Fore.GREEN + f"Saved {len(user_pass)} user:pass combinations to {output_file}" + Fore.RESET)

        return total_saved
    except Exception as e:
        print(Fore.RED + f"Error processing file: {e}" + Fore.RESET)
        return 0


def clear_combo_file(file_path, combo_type):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()

        cleaned_lines = set()
        valid_pattern = re.compile(r'^[^:]+:[^:]+$')

        for line in lines:
            line = line.strip()
            if not line or not valid_pattern.match(line):
                continue

            login, password = line.split(':', 1)
            if combo_type == 'email':
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', login):
                    continue
            elif combo_type == 'cpf':
                login = re.sub(r'[^0-9]', '', login)
                if not re.match(r'^\d{11}$', login):
                    continue
                line = f"{login}:{password}"

            cleaned_lines.add(line)

        if not cleaned_lines:
            print(Fore.YELLOW + "No valid combinations found after cleaning." + Fore.RESET)
            return

        backup_path = file_path + '.bak'
        os.rename(file_path, backup_path)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("\n".join(cleaned_lines) + "\n")

        print(Fore.GREEN + f"File cleaned successfully. Original file backed up as {backup_path}" + Fore.RESET)
        print(Fore.GREEN + f"Total valid combinations kept: {len(cleaned_lines)}" + Fore.RESET)
    except Exception as e:
        print(Fore.RED + f"Error cleaning file: {e}" + Fore.RESET)


def select_directory():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder_path = filedialog.askdirectory(title="Selecione a pasta com os arquivos")
    return folder_path


def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(title="Selecione o arquivo de texto", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
    return file_path


def process_files(folder_path, option, max_workers, target_domain=None):
    txt_files = find_txt_files(folder_path)

    if not txt_files:
        print(Fore.RED + "No .txt files found in the specified directory." + Fore.RESET)
        return

    total_files = len(txt_files)
    print(Fore.GREEN + f"Found {total_files} .txt files to process using {max_workers} CPU cores." + Fore.RESET)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_saved = 0
    batch_size = 1000
    batch_data = []

    if option == 1:
        output_file = os.path.join(CLOUD_RESULTS_DIR, "ULP", f"ULP_{timestamp}.txt")
        worker_func = _extract_ulp_worker
    elif option == 2:
        output_file = os.path.join(CLOUD_RESULTS_DIR, "LOGINPASS", f"logins_{timestamp}.txt")
        worker_func = _extract_login_pass_worker
    elif option == 3:
        domain_folder = os.path.join(CLOUD_RESULTS_DIR, "DOMAIN", target_domain)
        os.makedirs(domain_folder, exist_ok=True)
        output_file = os.path.join(domain_folder, f"{target_domain}_logins_{timestamp}.txt")
        worker_func = _extract_domain_logins_worker
    elif option == 6:
        cookies_dir = os.path.join(CLOUD_RESULTS_DIR, "cookies")
        os.makedirs(cookies_dir, exist_ok=True)
        output_file = os.path.join(cookies_dir, f"master_cookies_{timestamp}.txt")
        worker_func = _extract_cookies_worker
    else:
        return

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        if option == 3:
            futures = {executor.submit(worker_func, (fp, target_domain)): fp for fp in txt_files}
        else:
            futures = {executor.submit(worker_func, fp): fp for fp in txt_files}

        for i, future in enumerate(as_completed(futures), 1):
            data, error = future.result()

            if error:
                pass
            elif data:
                if isinstance(data, list):
                    batch_data.extend(data)
                else:
                    batch_data.append(data)

            if i % 100 == 0 or i == total_files:
                print(Fore.YELLOW + f"Processing file {i}/{total_files}" + Fore.RESET)

            if len(batch_data) >= batch_size:
                if option == 6:
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.write("\n".join(str(item) for item in batch_data) + "\n")
                    total_saved += len(batch_data)
                else:
                    total_saved += save_batch_data(batch_data, output_file)
                batch_data.clear()

    if batch_data:
        if option == 6:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "a", encoding="utf-8") as f:
                f.write("\n".join(str(item) for item in batch_data) + "\n")
            total_saved += len(batch_data)
        else:
            total_saved += save_batch_data(batch_data, output_file)

    if option == 6:
        print(Fore.GREEN + f"\nProcessamento concluído! Ficheiro único gerado em: {output_file}" + Fore.RESET)
        print(Fore.GREEN + f"Total cookies extracted: {total_saved}" + Fore.RESET)
    else:
        print(Fore.GREEN + f"\nResults saved to: {output_file}" + Fore.RESET)
        print(Fore.GREEN + f"Total new records added: {total_saved}" + Fore.RESET)


def main():
    create_results_directory()

    os.system('cls' if os.name == 'nt' else 'clear')
    options = """
[1] ULP FROM CLOUDS
[2] LOGIN:PASS FROM CLOUDS
[3] DOMAIN TO LOGIN:PASS
[4] ULP TO EMAIL:PASS / CPF:PASS / USER:PASS
[5] CLEAR COMBO FILE
[6] EXTRACT COOKIES FROM CLOUDS
"""
    print(Fore.CYAN + options + Fore.RESET)

    try:
        option = int(input('Choose an option: '))
        if option not in [1, 2, 3, 4, 5, 6]:
            raise ValueError
    except ValueError:
        print(Fore.RED + "Invalid option. Please choose between 1-6." + Fore.RESET)
        return

    if option == 4:
        print(Fore.CYAN + "Abrindo janela para selecionar o arquivo ULP..." + Fore.RESET)
        file_path = select_file()
        if not file_path:
            print(Fore.RED + "Nenhum arquivo selecionado." + Fore.RESET)
            return

        total_saved = process_ulp_to_formats(file_path)
        print(Fore.GREEN + f"\nTotal new records added: {total_saved}" + Fore.RESET)

    elif option == 5:
        print(Fore.CYAN + "Abrindo janela para selecionar o arquivo para limpar..." + Fore.RESET)
        file_path = select_file()
        if not file_path:
            print(Fore.RED + "Nenhum arquivo selecionado." + Fore.RESET)
            return

        print("\nChoose the combo type:")
        print("[1] EMAIL:PASS")
        print("[2] USER:PASS")
        print("[3] CPF:PASS")

        try:
            combo_type = int(input('Choose the combo type (1-3): '))
            if combo_type == 1:
                clear_combo_file(file_path, 'email')
            elif combo_type == 2:
                clear_combo_file(file_path, 'user')
            elif combo_type == 3:
                clear_combo_file(file_path, 'cpf')
            else:
                raise ValueError
        except ValueError:
            print(Fore.RED + "Invalid option. Please choose between 1-3." + Fore.RESET)
            return

    else:
        print(Fore.CYAN + "Abrindo janela para selecionar a pasta dos arquivos..." + Fore.RESET)
        folder_path = select_directory()
        if not folder_path:
            print(Fore.RED + "Nenhuma pasta selecionada." + Fore.RESET)
            return

        max_workers = None
        try:
            cpu_input = input(f'Enter number of CPU cores to use (Press Enter to use all available [{os.cpu_count()} max]): ').strip()
            if cpu_input:
                max_workers = int(cpu_input)
                if max_workers <= 0:
                    max_workers = None
        except ValueError:
            print(Fore.YELLOW + "Invalid input. Using all available CPU cores by default." + Fore.RESET)
            max_workers = None

        target_domain = None
        if option == 3:
            target_domain = input('Enter domain to search: ').strip()
            if not target_domain:
                print(Fore.RED + "Domain cannot be empty." + Fore.RESET)
                return

        process_files(folder_path, option, max_workers, target_domain)

    print(Fore.GREEN + "\nProcessing completed!" + Fore.RESET)


if __name__ == "__main__":
    main()