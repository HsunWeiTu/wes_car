#!/bin/bash
# Wes Car gz-sim 麥輪回歸測試（無頭）
# 驗證：URDF/SDF 轉換 + expressed_in 注入 + 前進/橫移/斜走全向運動
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
export IGN_GAZEBO_RESOURCE_PATH=/ws/install/simulation/share

XACRO=/ws/install/simulation/share/simulation/urdf/wes_car.urdf.xacro
xacro "$XACRO" -o /tmp/car.urdf
ign sdf -p /tmp/car.urdf > /tmp/car.sdf 2>/tmp/sdferr.txt
echo "### SDF error: $(grep -icE 'error|Exception' /tmp/sdferr.txt) 個"
sed -i 's|<fdir1>|<fdir1 ignition:expressed_in="base_footprint">|g' /tmp/car.sdf
echo "### expressed_in 注入數: $(grep -c expressed_in /tmp/car.sdf)（應為 4）"

cat > /tmp/w.sdf <<'EOF'
<?xml version="1.0"?>
<sdf version="1.8"><world name="wes_world">
<plugin filename="ignition-gazebo-physics-system" name="ignition::gazebo::systems::Physics"/>
<plugin filename="ignition-gazebo-user-commands-system" name="ignition::gazebo::systems::UserCommands"/>
<plugin filename="ignition-gazebo-scene-broadcaster-system" name="ignition::gazebo::systems::SceneBroadcaster"/>
<light type="directional" name="sun"><direction>0 0 -1</direction></light>
<model name="ground_plane"><static>true</static><link name="l">
<collision name="c"><geometry><plane><normal>0 0 1</normal><size>50 50</size></plane></geometry>
<surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision></link></model>
</world></sdf>
EOF
ign gazebo -s -r /tmp/w.sdf > /tmp/gz.log 2>&1 &
GZ=$!; sleep 5
ign service -s /world/wes_world/create --reqtype ignition.msgs.EntityFactory --reptype ignition.msgs.Boolean --timeout 5000 \
  --req "sdf_filename: \"/tmp/car.sdf\", name: \"wes_car\", pose: {position: {z: 0.06}}" >/dev/null
sleep 4
ros2 run ros_gz_bridge parameter_bridge /cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist >/tmp/b.log 2>&1 &
BR=$!; sleep 3

measure() {
  ( timeout 5 ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "$2" >/dev/null 2>&1 ) &
  timeout 5 ign topic -e -t /world/wes_world/dynamic_pose/info > /tmp/p.txt 2>/dev/null
  local x0 x1 y0 y1
  x0=$(grep -A5 '"wes_car"' /tmp/p.txt | grep -m1 "x:" | grep -oE "[-0-9.e]+" | head -1)
  x1=$(grep -A5 '"wes_car"' /tmp/p.txt | grep "x:" | tail -1 | grep -oE "[-0-9.e]+" | head -1)
  y0=$(grep -A5 '"wes_car"' /tmp/p.txt | grep -m1 "y:" | grep -oE "[-0-9.e]+" | head -1)
  y1=$(grep -A5 '"wes_car"' /tmp/p.txt | grep "y:" | tail -1 | grep -oE "[-0-9.e]+" | head -1)
  echo "### $1  Δx=$(python3 -c "print(round($x1-($x0),3))")  Δy=$(python3 -c "print(round($y1-($y0),3))")"
  sleep 1
}
measure "前進 vx=0.4 (預期 Δx>>0, Δy~0)" "{linear: {x: 0.4}}"
measure "橫移 vy=0.4 (預期 Δy>>0, Δx~0)" "{linear: {y: 0.4}}"
measure "斜走 vx=vy=0.3 (預期 Δx,Δy 皆>0)" "{linear: {x: 0.3, y: 0.3}}"
kill $BR $GZ 2>/dev/null
echo "### DONE"
