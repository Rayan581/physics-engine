import time

print("Starting physics engine...")
start = time.time()

from classes.game import Game
if __name__ == "__main__":
    game = Game()
    game.run()

end = time.time()
print(f"Simulation took {end - start:.4f} seconds.")