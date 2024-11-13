import sys
import argparse
import time
from roku import Roku
from rokucli.discover import discover_roku
from blessed import Terminal


default_usage_menu = (
        "  +-------------------------------+-------------------------+\n"
        "  | Back           B or <Esc>     | Replay          R       |\n"
        "  | Home           H              | Info/Settings   i       |\n"
        "  | Left           h or <Left>    | Rewind          r       |\n"
        "  | Down           j or <Down>    | Fast-Fwd        f       |\n"
        "  | Up             k or <Up>      | Play/Pause      <Space> |\n"
        "  | Right          l or <Right>   | Enter Text      /       |\n"
        "  | Ok/Enter       <Enter>        |                         |\n"
        "  +-------------------------------+-------------------------+\n"
        "   (press q to exit)\n")

tv_usage_menu = (
        "  +-------------------------------+-------------------------+\n"
        "  | Power          p              | Replay          R       |\n"
        "  | Back           B or <Esc>     | Info/Settings   i       |\n"
        "  | Home           H              | Rewind          r       |\n"
        "  | Left           h or <Left>    | Fast-Fwd        f       |\n"
        "  | Down           j or <Down>    | Play/Pause      <Space> |\n"
        "  | Up             k or <Up>      | Enter Text      /       |\n"
        "  | Right          l or <Right>   | Volume Up       V       |\n"
        "  | Ok/Enter       <Enter>        | Volume Down     v       |\n"
        "  |                               | Volume Mute     M       |\n"
        "  +-------------------------------+-------------------------+\n"
        "   (press q to exit)\n")


class RokuCLI():
    """ Command-line interpreter for processing user input and relaying
    commands to Roku """
    def __init__(self):
        self.term = Terminal()
        self.roku = None

    def parseargs(self):
        parser = argparse.ArgumentParser(
                description='Interactive command-line control of Roku devices')
        parser.add_argument(
                'ipaddr',
                nargs='?',
                help=('IP address of Roku to connect to. By default, will ' +
                      'automatically detect Roku within LAN.'))
        parser.add_argument(
            '-c', '--command',
            help='''Execute commands in script mode using comma-separated values.
                    Supports commands: home, up, down, left, right, select, etc.
                    Special commands: WAIT:seconds, TEXT:search_term

                    Examples:
                    home, down, TEXT:Search Term
                    volume-up, WAIT:1, volume-up''')
        return parser.parse_args()

    def execute_command(self, cmd):
        """Execute a single command"""
        if not (cmd.startswith('TEXT:') or cmd.startswith('WAIT:')):
            cmd = cmd.lower()

        cmd_func_map = {
            'power': self.roku.power,
            'back': self.roku.back,
            'home': self.roku.home,
            'left': self.roku.left,
            'down': self.roku.down,
            'up': self.roku.up,
            'right': self.roku.right,
            'replay': self.roku.replay,
            'info': self.roku.info,
            'reverse': self.roku.reverse,
            'forward': self.roku.forward,
            'play': self.roku.play,
            'pause': self.roku.play,  # Same as play
            'volume-up': self.roku.volume_up,
            'volume-down': self.roku.volume_down,
            'mute': self.roku.volume_mute,
            'select': self.roku.select,
            'enter': self.roku.select,  # Alias for select
        }

        if cmd in cmd_func_map:
            try:
                cmd_func_map[cmd]()
                return True
            except:
                print(f'Failed to execute command: {cmd}')
                return False
        return False

    def execute_text(self, text):
        """Execute text input"""
        try:
            for char in text:
                self.roku.literal(char)
            self.roku.enter()
            return True
        except:
            print(f'Failed to input text: {text}')
            return False

    def parse_and_execute_commands(self, command_string):
        """Parse and execute a command string"""
        # Split on comma and handle optional spaces
        commands = [cmd.strip() for cmd in command_string.split(',')]

        for cmd in commands:
            if not cmd:
                continue

            cmd = cmd.strip()
            
            # Handle wait command
            if cmd.upper().startswith('WAIT:'):
                try:
                    delay = float(cmd.split(':')[1])
                    time.sleep(delay)
                    continue
                except ValueError:
                    print(f'Invalid wait command: {cmd}')
                    return False
            
            # Handle text input
            if cmd.upper().startswith('TEXT:'):
                text = cmd[5:]
                if not self.execute_text(text):
                    return False
                continue
            
            # Handle regular commands
            if not self.execute_command(cmd):
                return False
            
            # Small delay between commands for stability
            time.sleep(0.1)
        
        return True

    def text_entry(self):
        """ Relay literal text entry from user to Roku until
        <Enter> or <Esc> pressed. """

        allowed_sequences = set([
            'KEY_ENTER',
            'KEY_ESCAPE',
            'KEY_DELETE',
            'KEY_BACKSPACE',
        ])

        sys.stdout.write('Enter text (<Esc> to abort) : ')
        sys.stdout.flush()

        # Track start column to ensure user doesn't backspace too far
        start_column = self.term.get_location()[1]
        cur_column = start_column

        with self.term.cbreak():
            val = ''
            while val != 'KEY_ENTER' and val != 'KEY_ESCAPE':
                val = self.term.inkey()
                if not val:
                    continue
                elif val.is_sequence:
                    val = val.name
                    if val not in allowed_sequences:
                        continue

                if val == 'KEY_ENTER':
                    self.roku.enter()
                elif val == 'KEY_ESCAPE':
                    pass
                elif val == 'KEY_DELETE' or val == 'KEY_BACKSPACE':
                    self.roku.backspace()
                    if cur_column > start_column:
                        sys.stdout.write(u'\b \b')
                        cur_column -= 1
                else:
                    self.roku.literal(val)
                    sys.stdout.write(val)
                    cur_column += 1
                sys.stdout.flush()

            # Clear to beginning of line
            sys.stdout.write(self.term.clear_bol)
            sys.stdout.write(self.term.move(self.term.height, 0))
            sys.stdout.flush()

    def run(self):
        args = self.parseargs()
        ipaddr = self.parseargs().ipaddr

        # If IP not specified, use Roku discovery and let user choose
        if ipaddr:
            self.roku = Roku(ipaddr)
        else:
            self.roku = discover_roku()

        if not self.roku:
            return

        # Script mode
        if args.command:
            success = self.parse_and_execute_commands(args.command)
            sys.exit(0 if success else 1)

        print(self.roku.device_info)
        is_tv = (self.roku.device_info.roku_type == "TV")

        if is_tv:
            print(tv_usage_menu)
        else:
            print(default_usage_menu)

        cmd_func_map = {
            'p':          self.roku.power,
            'B':          self.roku.back,
            'KEY_ESCAPE': self.roku.back,
            'H':          self.roku.home,
            'h':          self.roku.left,
            'KEY_LEFT':   self.roku.left,
            'j':          self.roku.down,
            'KEY_DOWN':   self.roku.down,
            'k':          self.roku.up,
            'KEY_UP':     self.roku.up,
            'l':          self.roku.right,
            'KEY_RIGHT':  self.roku.right,
            'KEY_ENTER':  self.roku.select,
            'R':          self.roku.replay,
            'i':          self.roku.info,
            'r':          self.roku.reverse,
            'f':          self.roku.forward,
            ' ':          self.roku.play,
            '/':          self.text_entry}

        if is_tv:
            cmd_func_map['V'] = self.roku.volume_up
            cmd_func_map['v'] = self.roku.volume_down
            cmd_func_map['M'] = self.roku.volume_mute

        # Main interactive loop
        with self.term.cbreak():
            val = ''
            while val.lower() != 'q':
                val = self.term.inkey()
                if not val:
                    continue
                if val.is_sequence:
                    val = val.name
                if val in cmd_func_map:
                    try:
                        cmd_func_map[val]()
                    except:
                        print('Unable to communicate with roku at ' +
                              str(self.roku.host) + ':' + str(self.roku.port))
                        sys.exit(1)


def main():
    RokuCLI().run()

if __name__ == '__main__':
    main()
