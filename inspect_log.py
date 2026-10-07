import csv
from pathlib import Path


def main() -> None:
    # Localizar o log do robô 1.
    project_dir = Path(__file__).resolve().parent
    csv_path = project_dir / "data" / "robot1_s1.csv"

    with csv_path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        # Apresentar os nomes das colunas.
        print("Colunas disponíveis:")
        for column in reader.fieldnames:
            print(f"- {column}")

        # Ler e apresentar apenas os primeiros três registos.
        record_count = 0

        for row in reader:
            record_count += 1

            print(f"\nRegisto {record_count}:")
            print(f"Segundos: {row['header.stamp.secs']}")
            print(f"Nanossegundos: {row['header.stamp.nsecs']}")
            print(f"Referencial: {row['header.frame_id']}")
            print(f"Posição X: {row['pose.pose.position.x']}")
            print(f"Posição Y: {row['pose.pose.position.y']}")
            print(f"Posição Z: {row['pose.pose.position.z']}")

            # Terminar o ciclo depois de apresentar o terceiro.
            if record_count == 3:
                break


if __name__ == "__main__":
    main()