from data_parser import parse_seed_data
import json

def test():
    print("Testing parse_seed_data...")
    result = parse_seed_data()
    print(f"Rooms: {len(result['rooms'])}")
    print(f"Workloads: {len(result['workloads'])}")
    print(f"Requirements: {len(result['requirements'])}")

if __name__ == "__main__":
    test()
