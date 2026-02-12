function filter(inputs, minValues, maxValues, multiplexIndex)
{
    // 1. Convert Degrees to Radians for Math functions
    var degToRad = Math.PI / 180;
    var rx = inputs[0] * degToRad;
    var ry = inputs[1] * degToRad;
    var rz = inputs[2] * degToRad;
    
    // 2. Unpack FT Data
    var f_tool = [inputs[3], inputs[4], inputs[5]];
    var t_tool = [inputs[6], inputs[7], inputs[8]];

    // 3. Pre-calculate Trigonometry
    var cx = Math.cos(rx);
    var sx = Math.sin(rx);
    var cy = Math.cos(ry);
    var sy = Math.sin(ry);
    var cz = Math.cos(rz);
    var sz = Math.sin(rz);

    // 4. Construct Rotation Matrix (Euler XYZ convention)
    // R = Rz * Ry * Rx
    var r11 = cy * cz;
    var r12 = sx * sy * cz - cx * sz;
    var r13 = cx * sy * cz + sx * sz;
    
    var r21 = cy * sz;
    var r22 = sx * sy * sz + cx * cz;
    var r23 = cx * sy * sz - sx * cz;
    
    var r31 = -sy;
    var r32 = sx * cy;
    var r33 = cx * cy;

    // 5. Transform Force Vector (Tool to Base)
    var fb_x = r11 * f_tool[0] + r12 * f_tool[1] + r13 * f_tool[2];
    var fb_y = r21 * f_tool[0] + r22 * f_tool[1] + r23 * f_tool[2];
    var fb_z = r31 * f_tool[0] + r32 * f_tool[1] + r33 * f_tool[2];

    // 6. Transform Torque Vector (Tool to Base)
    var tb_x = r11 * t_tool[0] + r12 * t_tool[1] + r13 * t_tool[2];
    var tb_y = r21 * t_tool[0] + r22 * t_tool[1] + r23 * t_tool[2];
    var tb_z = r31 * t_tool[0] + r32 * t_tool[1] + r33 * t_tool[2];

    // 7. Return result array (9 length)
    // [F_base_x, F_base_y, F_base_z, T_base_x, T_base_y, T_base_z, 0, 0, 0]
    return [fb_x, fb_y, fb_z, tb_x, tb_y, tb_z, 0, 0, 0];
}
