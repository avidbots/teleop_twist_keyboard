# teleop_twist_keyboard
Generic Keyboard Teleoperation for ROS

## Run

```sh
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Publishing to a different topic (in this case `my_cmd_vel`).
```sh
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=my_cmd_vel
```

## Usage

```
This node takes keypresses from the keyboard and publishes them as Twist
messages. It works best with a US keyboard layout.
---------------------------
Moving around:
   u    i    o
   j    k    l
   m    ,    .

For Holonomic mode (strafing), hold down the shift key:
---------------------------
   U    I    O
   J    K    L
   M    <    >

t : up (+z)
b : down (-z)

anything else : stop

q/z : increase/decrease max speeds by 10%
w/x : increase/decrease only linear speed by 10%
e/c : increase/decrease only angular speed by 10%

CTRL-C to quit
```

## Parameters
- `stamped (bool, default: false)`
  - If false (the default), publish a `geometry_msgs/msg/Twist` message.  If true, publish a `geometry_msgs/msg/TwistStamped` message.
- `frame_id (string, default: '')`
  - When `stamped` is true, the frame_id to use when publishing the `geometry_msgs/msg/TwistStamped` message.
- `speed (double, default: 0.5)`
  - The speed the node starts with by default.
- `turn (double, default: 1.0)`
  - The turn rate (rad/s) the node starts with by default.
- `deadman_timeout (double, default: 0.1)`
  - Deadman timeout in seconds. The node will continue publishing the last
    velocity command for the configured timeout after the last keypress. If no
    keypress occurs and the timeout expires, motion commands will stop. This
    package in this repository has been cloned and extended to include this
    parameter to provide a simple deadman behavior for safety and convenience.

## Syncing with upstream

This repository is a fork of the original teleop_twist_keyboard package. To keep
your fork up to date with the original source (https://github.com/ros2/teleop_twist_keyboard),
add the original repository as an "upstream" remote and pull changes regularly.

Below are example git commands you can run from the root of this package's
git repository (the directory that contains this `README.md`). Replace
`<branch>` with the branch you track (for example `main` or `master`).

1) Add the upstream remote (only needed once):

```sh
git remote add upstream https://github.com/ros2/teleop_twist_keyboard.git
```

2) Fetch the latest changes from upstream:

```sh
git fetch upstream
```

3) Rebase your tracked branch onto upstream (keeps a linear history):

```sh
git checkout <branch>
git rebase upstream/<branch>
```

If you prefer to merge instead of rebase (preserves the exact upstream history but creates a merge commit):

```sh
git checkout <branch>
git merge upstream/<branch>
```

4) If you rebased and already pushed your local branch to your origin remote,
you will need to force-push the updated branch to your fork:

```sh
git push --force-with-lease origin <branch>
```

If you merged, a normal push is sufficient:

```sh
git push origin <branch>
```

Notes and tips:
- If you have local changes or feature branches, rebase feature branches onto
  the updated tracked branch to integrate upstream fixes.
- Use `--force-with-lease` rather than `--force` to reduce the chance of
  overwriting others' work on the remote.
- Resolve conflicts during rebase or merge using your preferred merge tool,
  then continue the rebase with `git rebase --continue`.
- Always run your package's tests or a quick build after syncing to ensure
  the upstream changes didn't break local modifications.

