import socket
import threading
import time

# 🔹 서버 설정
HOST = '192.168.178.37'
PORTS = [5001, 5002, 5003]

# 🔹 마스터 서버 정보
MASTER_SERVER = '192.168.0.201'
MASTER_PORT = 5000

# 🔹 특정 포트만 전송 (5001번)
FORWARD_PORT = 5001

# 🔹 클라이언트 소켓 저장
client_sockets = {}

def master_connection_thread():
    """마스터 서버와 지속적으로 연결을 유지하며 메시지를 주고받는 스레드"""
    global master_socket
    while True:
        try:
            print(f"[마스터 서버 연결 시도] {MASTER_SERVER}:{MASTER_PORT}")
            master_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            master_socket.connect((MASTER_SERVER, MASTER_PORT))
            print(f"[마스터 서버 연결됨] {MASTER_SERVER}:{MASTER_PORT}")

            while True:
                data = master_socket.recv(1024)
                if not data:
                    print("[마스터 서버 연결 종료됨. 재시도 중...]")
                    break
                
                decoded_data = data.decode().strip()
                print(f"[마스터 서버 수신] {decoded_data}")

                # 받은 메시지를 5002번 포트로 포워딩
                if decoded_data == "shipped":
                    forward_message_to_5002(decoded_data)

        except Exception as e:
            print(f"[마스터 서버 오류] {str(e)}. 3초 후 재연결 시도...")
            time.sleep(3)  # 오류 발생 시 재연결 대기

def send_to_master(data):
    """마스터 서버에 메시지를 전송하는 함수"""
    global master_socket
    try:
        if master_socket:
            print(f"[마스터 서버 전송] {data}")
            master_socket.sendall(data.encode())
        else:
            print("[마스터 서버 전송 실패] 연결이 설정되지 않음")
    except Exception as e:
        print(f"[마스터 서버 전송 오류] {str(e)}")

# 🔹 5002번 포트의 기존 클라이언트에게 메시지 전송
def forward_message_to_5002(message):
    global client_sockets
    if 5002 in client_sockets:
        try:
            print(f"[Forward] 5002번 포트의 기존 클라이언트에게 메시지 전송 : {message}")
            conn = client_sockets[5002]
            conn.sendall(message.encode())
        except Exception as e:
            print(f"[Forward] 5002 메시지 전송 오류: {e}")
            
def forward_message_to_5003(message):
    global client_sockets
    if 5003 in client_sockets:
        try:
            print(f"[Forward] 5003번 포트의 기존 클라이언트에게 메시지 전송 : {message}")
            conn = client_sockets[5003]
            conn.sendall((message + "\n").encode())
        except Exception as e:
            print(f"[Forward] 5003 메시지 전송 오류: {e}")


# 🔹 클라이언트 핸들러 (연결된 소켓 저장)
def handle_client(conn, addr, port):
    print(f"[접속] 포트 {port} │ 클라이언트 {addr[0]}:{addr[1]}")
    
    # 클라이언트 소켓 저장
    global client_sockets
    client_sockets[port] = conn

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            decoded_data = data.decode().strip()
            print(f"[수신] 포트 {port} ({addr[0]}) → {decoded_data}")

            # 5001번 포트에서 "start" 수신 시 5002번 포트의 기존 클라이언트에게 전달 / 앱으로 시작버튼을 누르면 파이에 데이터를 전송, amr이 동작하도록 한다 이것으로 앱의 역할은 일단 종료
            if port == 5001 and decoded_data == "start":
                forward_message_to_5002(decoded_data)
                conn.sendall(b"Message Sent to Pi")

            # 라즈베리 파이가 1번 위치에 도달하면 문 개방 요청. 이를 아두이노에 전달한다
            elif port == 5002 and decoded_data == "open":
                forward_message_to_5003()
                conn.sendall(b"Message Sent to Arduino")
            # 라즈베리가 문을 통과한 뒤 2번 위치에 도달하면 문 폐쇄 요청. 이를 아두이노에 전달한다.
            elif port == 5002 and decoded_data == "close":
                forward_message_to_5003(decoded_data)
                conn.sendall(b"Message Sent to Arduino")

            #라즈베리가 로봇의 앞(3번위치)에 도달하면 도착 신호를 보냄. 이를 abb에 전달해 적재 프로세스를 시작한다. (라즈베리는 도달 di신호를 받으면 서보와 컨베이어를 동작시킨다)
            elif port == 5002 and decoded_data == "arrived":
                send_to_master(decoded_data)
                conn.sendall(b"Message Sent to ABB")

            #로봇이 적재를 완료하면 완료 신호를 전달. 이를 파이에 전송해 amr이 다시 출발 하도록 명령 -> 위의 메인서버와의 쓰레드 확인
            
            #로봇이 2번위치에 도달. 문 개방 요청을 아두이노에 전달
            elif port == 5002 and decoded_data == "open":
                forward_message_to_5003(decoded_data)
                conn.sendall(b"Message Sent to Arduino")
            #로봇이 1번위치에 도달. 문 폐쇄 요청을 아두이노에 전달
            elif port == 5002 and decoded_data == "close":
                forward_message_to_5003(decoded_data)
                conn.sendall(b"Message Sent to Arduino")

            #로봇이 하역장소(4번위치)에 도달. 파이가 서버에 작업완료 메세지 전송 (파이는 2번서보와 컨베이어를 동작시키고 난 뒤 작업완료 메세지를 보낸다.). 파이에게 리셋 메세지 전송, amr이 충전독으로 이동
            elif port == 5002 and decoded_data == "proc_end":
                forward_message_to_5002("reset")
                conn.sendall(b"Message Sent to Pi")

            else:
                conn.sendall(b"ACK from server")
        except Exception as e:
            print(f"[에러] {str(e)}")
            break

    print(f"[연결종료] 포트 {port} │ {addr[0]}:{addr[1]}")
    del client_sockets[port]
    conn.close()

def start_server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, port))
    server.listen()
    print(f"[서버시작] {HOST}:{port} 대기중...")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr, port))
        thread.start()

if __name__ == "__main__":
    for port in PORTS:
        threading.Thread(target=start_server, args=(port,), daemon=True).start()
    
    while True:
        time.sleep(1)

            #로봇이 적재를 완료하면 완료 신호를 전달. 이를 파이에 전송해 amr이 다시 출발 하도록 명령
            