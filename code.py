"""NeoTrellis M4 code entry point."""

if __name__ == '__main__':
    # Uncomment one of the lines below to run that app
    # (can only run one at a time)

    # import singleloopstation

    from multiloopstation import Board
    board = Board()
    board.loop()
    
    # import pause