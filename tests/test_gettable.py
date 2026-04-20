import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from entities import Entity, ResourcePool

def test():
    print("Testing Entity.get()...")
    e = Entity(name="Test", type="player", hp=10)
    print(f"Type: {e.get('type')}")
    print(f"HP: {e.get('hp')}")
    print(f"Missing: {e.get('nonexistent', 'Fallback')}")
    
    print("\nTesting nested ResourcePool.get()...")
    res = e.resources
    print(f"Stamina: {res.get('stamina')}")
    
    print("\nTest Complete.")

if __name__ == "__main__":
    try:
        test()
    except Exception as ex:
        print(f"ERORR: {ex}")
