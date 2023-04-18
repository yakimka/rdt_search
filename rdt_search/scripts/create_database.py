import argparse

from rdt_search import db

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_file", type=str)
    parser.add_argument("--csv_file", type=str)
    args = parser.parse_args()

    with open(args.csv_file, "r") as fp:
        data = db.stream_data(fp)

        cursor = db.get_cursor(args.db_file)
        db.create_index(cursor)
        db.insert_rows(cursor, data)
        cursor.connection.commit()
        cursor.connection.close()
        print("Done!")
