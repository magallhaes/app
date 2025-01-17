from credentials_manager import CredentialsManager
import argparse

def main():
    parser = argparse.ArgumentParser(description='Gerenciador de Usuários')
    parser.add_argument('action', choices=['add', 'remove', 'list'], help='Ação a ser executada')
    parser.add_argument('--username', help='Nome de usuário')
    parser.add_argument('--password', help='Senha do usuário')
    parser.add_argument('--email', help='Email do usuário')
    parser.add_argument('--name', help='Nome completo do usuário')

    args = parser.parse_args()
    manager = CredentialsManager()

    if args.action == 'add':
        if not all([args.username, args.password]):
            print("Username e password são obrigatórios para adicionar usuário")
            return
        try:
            manager.add_user(args.username, args.password, args.email or "", args.name or "")
            print(f"Usuário {args.username} adicionado com sucesso!")
        except ValueError as e:
            print(f"Erro: {e}")
    
    elif args.action == 'remove':
        if not args.username:
            print("Username é obrigatório para remover usuário")
            return
        if manager.remove_user(args.username):
            print(f"Usuário {args.username} removido com sucesso!")
        else:
            print(f"Usuário {args.username} não encontrado")
    
    elif args.action == 'list':
        credentials = manager._load_credentials()
        print("\nUsuários cadastrados:")
        for username, info in credentials.items():
            print(f"\nUsername: {username}")
            print(f"Email: {info.get('email', 'N/A')}")
            print(f"Nome: {info.get('name', 'N/A')}")

if __name__ == "__main__":
    main()