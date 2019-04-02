"""NeoTrellis M4 code entry point."""

if __name__ == '__main__':
    # import singleloopstation

    from multiloopstation import Board
    board = Board()
    board.loop()
    
    # import pause