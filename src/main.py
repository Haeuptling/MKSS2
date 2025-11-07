from robot import Robot

def main():
    robot = Robot(id=1, position=(0, 0), energy=100)
    print("Robot ID:", robot.id)

if __name__ == "__main__":
    main()