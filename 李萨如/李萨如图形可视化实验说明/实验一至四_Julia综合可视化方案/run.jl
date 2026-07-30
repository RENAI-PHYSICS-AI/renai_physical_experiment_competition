import Pkg

const LAB_DIR = @__DIR__
Pkg.activate(LAB_DIR)

if !("--no-instantiate" in ARGS)
    Pkg.instantiate()
end

using Dates
using GLMakie
using LinearAlgebra
using Printf

GLMakie.activate!(title = "李萨如图形综合实验：实验一至四")

const TWO_PI = 2pi
const ACCENT_X = RGBf(0.18, 0.78, 0.92)
const ACCENT_Y = RGBf(0.94, 0.35, 0.50)
const ACCENT_MAJOR = RGBf(1.00, 0.72, 0.24)
const ACCENT_MINOR = RGBf(0.36, 0.82, 0.55)
const MUTED = RGBf(0.58, 0.62, 0.70)
const PANEL_BG = RGBf(0.075, 0.085, 0.105)
const BUTTON_BG = RGBf(0.13, 0.15, 0.19)
const BUTTON_ACTIVE = RGBf(0.15, 0.42, 0.58)

const MODE_ORDER = (:phase, :amplitude, :ratio, :detune)
const MODE_NAMES = Dict(
    :phase => "实验一 · 相位差",
    :amplitude => "实验二 · 振幅比",
    :ratio => "实验三 · 有理频率比",
    :detune => "实验四 · 频率失谐",
)
const MODE_FILES = Dict(
    :phase => "phase",
    :amplitude => "amplitude",
    :ratio => "ratio",
    :detune => "detune",
)

function first_existing_font(candidates)
    for candidate in candidates
        isfile(candidate) && return candidate
    end
    error(
        "未找到可显示中文的字体。请安装微软雅黑、苹方或 Noto Sans CJK，" *
        "再在 first_existing_font 中加入字体文件路径。",
    )
end

function cjk_font_family()
    regular = first_existing_font([
        raw"C:\Windows\Fonts\msyh.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ])
    bold_candidates = [
        raw"C:\Windows\Fonts\msyhbd.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    ]
    bold_index = something(findfirst(isfile, bold_candidates), 0)
    bold = bold_index == 0 ? regular : bold_candidates[bold_index]
    return (; regular, bold)
end

function ellipse_geometry(amplitude_x, amplitude_y, phase)
    map_matrix = [
        amplitude_x 0.0
        amplitude_y * cos(phase) amplitude_y * sin(phase)
    ]
    factor = svd(map_matrix)
    return collect(factor.S), Matrix(factor.U)
end

function ellipse_axis_segments(semiaxes, directions)
    major = semiaxes[1] .* directions[:, 1]
    minor = semiaxes[2] .* directions[:, 2]
    return (
        Point2f[
            Point2f(-major[1], -major[2]),
            Point2f(major[1], major[2]),
        ],
        Point2f[
            Point2f(-minor[1], -minor[2]),
            Point2f(minor[1], minor[2]),
        ],
    )
end

function shape_name(phase; atol = deg2rad(0.5))
    wrapped = mod(phase, TWO_PI)
    if min(wrapped, TWO_PI - wrapped) <= atol
        return "正斜率直线"
    elseif abs(wrapped - pi) <= atol
        return "负斜率直线"
    elseif abs(abs(sin(wrapped)) - 1.0) <= sin(atol)
        return "圆"
    end
    return "椭圆"
end

function rotation_name(phase)
    s = sin(phase)
    if abs(s) < 1.0e-8
        return "往复运动"
    elseif s > 0
        return "顺时针"
    end
    return "逆时针"
end

function phase_ellipse(amplitude, frequency, phase, sample_count)
    period = inv(frequency)
    time = collect(range(0.0, period; length = sample_count))
    theta = TWO_PI .* frequency .* time
    x = amplitude .* sin.(theta)
    y = amplitude .* sin.(theta .+ phase)
    semiaxes, directions = ellipse_geometry(amplitude, amplitude, phase)
    residuals =
        x .^ 2 .+ y .^ 2 .- 2 .* x .* y .* cos(phase) .-
        amplitude^2 * sin(phase)^2
    phase_grid = collect(0.0:1.0:360.0)
    ratio_curve = map(phase_grid) do degree
        axes, _ = ellipse_geometry(amplitude, amplitude, deg2rad(degree))
        axes[1] < 1.0e-12 ? 0.0 : axes[2] / axes[1]
    end
    return (;
        time,
        x,
        y,
        trajectory = Point2f.(x, y),
        semiaxes,
        directions,
        residual = maximum(abs.(residuals)),
        phase_grid,
        ratio_curve,
        period,
        frequency_x = frequency,
        frequency_y = frequency,
    )
end

function amplitude_ellipse(amplitude_x, amplitude_y, frequency, phase, sample_count)
    period = inv(frequency)
    time = collect(range(0.0, period; length = sample_count))
    theta = TWO_PI .* frequency .* time
    x = amplitude_x .* sin.(theta)
    y = amplitude_y .* sin.(theta .+ phase)
    normalized = Point2f.(x ./ amplitude_x, y ./ amplitude_y)
    semiaxes, directions = ellipse_geometry(amplitude_x, amplitude_y, phase)
    xn = x ./ amplitude_x
    yn = y ./ amplitude_y
    residuals = xn .^ 2 .+ yn .^ 2 .- 2 .* xn .* yn .* cos(phase) .- sin(phase)^2
    return (;
        time,
        x,
        y,
        trajectory = Point2f.(x, y),
        normalized,
        semiaxes,
        directions,
        residual = maximum(abs.(residuals)),
        area = pi * amplitude_x * amplitude_y * abs(sin(phase)),
        period,
        frequency_x = frequency,
        frequency_y = frequency,
    )
end

function ratio_curve(amplitude, base_frequency, m, n, phase, sample_count)
    common_divisor = gcd(m, n)
    reduced_m = m ÷ common_divisor
    reduced_n = n ÷ common_divisor
    frequency_x = m * base_frequency
    frequency_y = n * base_frequency
    close_period = inv(common_divisor * base_frequency)
    time = collect(range(0.0, close_period; length = sample_count))
    x = amplitude .* sin.(TWO_PI .* frequency_x .* time)
    y = amplitude .* sin.(TWO_PI .* frequency_y .* time .+ phase)
    x0 = first(x)
    y0 = first(y)
    closure_distance = sqrt.((x .- x0) .^ 2 .+ (y .- y0) .^ 2)
    return (;
        time,
        x,
        y,
        trajectory = Point2f.(x, y),
        closure_distance,
        close_period,
        common_divisor,
        reduced_m,
        reduced_n,
        frequency_x,
        frequency_y,
        endpoint_error = last(closure_distance),
    )
end

function detune_frame(amplitude, frequency, delta_frequency, initial_phase, sample_count, progress)
    frequency_y = frequency + delta_frequency
    shape_period = abs(delta_frequency) < 1.0e-12 ? Inf : inv(abs(delta_frequency))
    animation_span = isfinite(shape_period) ? shape_period : 2 * inv(frequency)
    current_time = progress * animation_span
    window_length = inv(frequency)
    time = collect(range(current_time - window_length, current_time; length = sample_count))
    x = amplitude .* sin.(TWO_PI .* frequency .* time)
    y = amplitude .* sin.(TWO_PI .* frequency_y .* time .+ initial_phase)
    effective_phase = mod(TWO_PI * delta_frequency * current_time + initial_phase, TWO_PI)

    phase_time = collect(range(0.0, animation_span; length = sample_count))
    unwrapped_cycles =
        initial_phase / TWO_PI .+ delta_frequency .* phase_time
    return (;
        time,
        x,
        y,
        trajectory = Point2f.(x, y),
        shape_period,
        current_time,
        effective_phase,
        phase_time,
        unwrapped_cycles,
        frequency_x = frequency,
        frequency_y,
    )
end

function direction_arrow(
    amplitude_x,
    amplitude_y,
    frequency_x,
    frequency_y,
    phase,
    time,
)
    point = [
        amplitude_x * sin(TWO_PI * frequency_x * time),
        amplitude_y * sin(TWO_PI * frequency_y * time + phase),
    ]
    velocity = [
        TWO_PI * frequency_x * amplitude_x * cos(TWO_PI * frequency_x * time),
        TWO_PI * frequency_y * amplitude_y * cos(TWO_PI * frequency_y * time + phase),
    ]
    speed = norm(velocity)
    speed < 1.0e-10 && return Point2f[Point2f(point...)]

    direction = velocity ./ speed
    scale = max(amplitude_x, amplitude_y)
    arrow_length = max(0.16, 0.25 * scale)
    tip = point .+ arrow_length .* direction
    angle = atan(direction[2], direction[1])
    head_length = 0.08 * max(scale, 0.6)
    left = tip .- head_length .* [cos(angle - pi / 6), sin(angle - pi / 6)]
    right = tip .- head_length .* [cos(angle + pi / 6), sin(angle + pi / 6)]
    separator = Point2f(NaN, NaN)
    return Point2f[
        Point2f(point...),
        Point2f(tip...),
        separator,
        Point2f(tip...),
        Point2f(left...),
        separator,
        Point2f(tip...),
        Point2f(right...),
    ]
end

function set_block_visible!(block, visible)
    block.blockscene.visible[] = visible
    return nothing
end

function time_colors(count)
    count <= 1 && return [0.0]
    return collect(range(0.0, 1.0; length = count))
end

function write_csv(path, mode, parameters, data)
    open(path, "w") do io
        println(io, "# mode,$(MODE_NAMES[mode])")
        for (key, value) in pairs(parameters)
            println(io, "# $(key),$(value)")
        end
        println(io, "t_s,x,y")
        for i in eachindex(data.time)
            @printf(io, "%.10f,%.10f,%.10f\n", data.time[i], data.x[i], data.y[i])
        end
    end
end

function build_lab()
    set_theme!(
        theme_dark();
        fontsize = 15,
        fonts = cjk_font_family(),
        backgroundcolor = RGBf(0.045, 0.050, 0.065),
        Axis = (
            backgroundcolor = PANEL_BG,
            xgridcolor = (:white, 0.08),
            ygridcolor = (:white, 0.08),
            titlecolor = RGBf(0.84, 0.86, 0.90),
            topspinevisible = false,
            rightspinevisible = false,
        ),
    )

    figure = Figure(size = (1360, 820), figure_padding = 14)
    Label(
        figure[1, 1:3],
        "李萨如图形综合实验：相位、振幅比、频率比与频率失谐",
        fontsize = 25,
        font = :bold,
        halign = :left,
        color = :white,
    )

    mode = Observable(:phase)
    mode_grid = GridLayout()
    figure[2, 1:3] = mode_grid
    mode_buttons = Dict{Symbol, Button}()
    for (index, key) in enumerate(MODE_ORDER)
        button = Button(
            mode_grid[1, index],
            label = MODE_NAMES[key],
            height = 29,
            buttoncolor = key == :phase ? BUTTON_ACTIVE : BUTTON_BG,
            labelcolor = :white,
        )
        mode_buttons[key] = button
    end

    wave_axis = Axis(
        figure[3, 1],
        title = "X、Y 方向时域波形",
        xlabel = "时间 t / s",
        ylabel = "位移",
    )
    trajectory_title = Observable("李萨如主轨迹")
    trajectory_axis = Axis(
        figure[3, 2],
        title = trajectory_title,
        xlabel = "x",
        ylabel = "y",
        aspect = DataAspect(),
    )

    aux_phase_axis = Axis(
        figure[3, 3],
        title = "相位差与椭圆半轴比",
        xlabel = "φ / degree",
        ylabel = "b/a",
    )
    aux_normal_axis = Axis(
        figure[3, 3],
        title = "振幅归一化轨迹",
        xlabel = "x/A",
        ylabel = "y/B",
        aspect = DataAspect(),
    )
    aux_ratio_axis = Axis(
        figure[3, 3],
        title = "轨迹返回起点的距离",
        xlabel = "t / Tclose",
        ylabel = "d(t)",
    )
    aux_detune_axis = Axis(
        figure[3, 3],
        title = "等效相位的累积",
        xlabel = "t / Tshape",
        ylabel = "Δφ / 2π",
    )
    auxiliary_axes = Dict(
        :phase => aux_phase_axis,
        :amplitude => aux_normal_axis,
        :ratio => aux_ratio_axis,
        :detune => aux_detune_axis,
    )

    controls = GridLayout()
    figure[4, 1:3] = controls
    Label(controls[1, 1:2], "实验参数", font = :bold, halign = :left, color = :white)
    basic_grid = GridLayout()
    special_grid = GridLayout()
    motion_grid = GridLayout()
    controls[2, 1] = basic_grid
    controls[2, 2] = special_grid
    controls[2, 3] = motion_grid

    amplitude_a_slider = Slider(
        basic_grid[1, 2],
        range = 0.20:0.05:2.00,
        startvalue = 1.00,
        update_while_dragging = false,
    )
    amplitude_b_slider = Slider(
        basic_grid[2, 2],
        range = 0.20:0.05:2.00,
        startvalue = 0.65,
        update_while_dragging = false,
    )
    frequency_slider = Slider(
        basic_grid[3, 2],
        range = 0.50:0.10:5.00,
        startvalue = 1.00,
        update_while_dragging = false,
    )
    phase_slider = Slider(
        basic_grid[4, 2],
        range = 0:1:360,
        startvalue = 60,
        update_while_dragging = false,
    )

    amplitude_a_label_text = Observable("共同振幅 A")
    frequency_label_text = Observable("共同频率 f")
    phase_label_text = Observable("相位差 φ")
    amplitude_a_label = Label(basic_grid[1, 1], amplitude_a_label_text, halign = :right)
    amplitude_b_label = Label(basic_grid[2, 1], "Y 振幅 B", halign = :right)
    frequency_label = Label(basic_grid[3, 1], frequency_label_text, halign = :right)
    phase_label = Label(basic_grid[4, 1], phase_label_text, halign = :right)
    amplitude_a_value = Label(
        basic_grid[1, 3],
        lift(value -> @sprintf("%.2f", value), amplitude_a_slider.value),
    )
    amplitude_b_value = Label(
        basic_grid[2, 3],
        lift(value -> @sprintf("%.2f", value), amplitude_b_slider.value),
    )
    frequency_value = Label(
        basic_grid[3, 3],
        lift(value -> @sprintf("%.2f Hz", value), frequency_slider.value),
    )
    phase_value = Label(
        basic_grid[4, 3],
        lift(value -> @sprintf("%d°", value), phase_slider.value),
    )

    m_slider = Slider(
        special_grid[1, 2],
        range = 1:1:6,
        startvalue = 2,
        update_while_dragging = false,
    )
    n_slider = Slider(
        special_grid[2, 2],
        range = 1:1:6,
        startvalue = 3,
        update_while_dragging = false,
    )
    detune_slider = Slider(
        special_grid[3, 2],
        range = -0.40:0.01:0.40,
        startvalue = 0.05,
        update_while_dragging = false,
    )
    sample_slider = Slider(
        special_grid[4, 2],
        range = 300:100:2000,
        startvalue = 1000,
        update_while_dragging = false,
    )
    m_label = Label(special_grid[1, 1], "频率整数 m", halign = :right)
    n_label = Label(special_grid[2, 1], "频率整数 n", halign = :right)
    detune_label = Label(special_grid[3, 1], "频率差 Δf", halign = :right)
    sample_label = Label(special_grid[4, 1], "采样点数 N", halign = :right)
    m_value = Label(special_grid[1, 3], lift(string, m_slider.value))
    n_value = Label(special_grid[2, 3], lift(string, n_slider.value))
    detune_value = Label(
        special_grid[3, 3],
        lift(value -> @sprintf("%+.2f Hz", value), detune_slider.value),
    )
    sample_value = Label(special_grid[4, 3], lift(string, sample_slider.value))

    progress_slider = Slider(
        motion_grid[1, 2],
        range = 0:1:1000,
        startvalue = 0,
        update_while_dragging = true,
    )
    speed_slider = Slider(
        motion_grid[2, 2],
        range = 0.25:0.25:2.00,
        startvalue = 0.50,
        update_while_dragging = true,
    )
    progress_label_text = Observable("质点进程")
    Label(motion_grid[1, 1], progress_label_text, halign = :right)
    Label(motion_grid[2, 1], "播放速度", halign = :right)
    Label(
        motion_grid[1, 3],
        lift(value -> @sprintf("%.1f%%", value / 10), progress_slider.value),
    )
    Label(
        motion_grid[2, 3],
        lift(value -> @sprintf("%.2f×", value), speed_slider.value),
    )

    playing = Observable(false)
    play_label = lift(value -> value ? "暂停" : "播放", playing)
    command_style = (
        height = 29,
        buttoncolor = BUTTON_BG,
        labelcolor = :white,
    )
    command_grid = GridLayout()
    motion_grid[3:4, 1:3] = command_grid
    play_button = Button(command_grid[1, 1]; label = play_label, command_style...)
    reset_button = Button(command_grid[1, 2]; label = "重置", command_style...)
    export_button = Button(
        command_grid[2, 1:2];
        label = "导出 PNG + CSV",
        command_style...,
    )

    status = Observable("就绪")
    status_color = lift(text -> startswith(text, "正在") ? ACCENT_MAJOR : ACCENT_MINOR, status)
    Label(controls[1, 3], status, color = status_color, halign = :right, font = :bold)

    analysis = GridLayout()
    figure[5, 1:3] = analysis
    Label(analysis[1, 1:4], "实时分析", font = :bold, halign = :left, color = :white)
    metric_1 = Observable("")
    metric_2 = Observable("")
    metric_3 = Observable("")
    metric_4 = Observable("")
    detail = Observable("")
    Label(analysis[2, 1], metric_1, halign = :left)
    Label(analysis[2, 2], metric_2, halign = :left)
    Label(analysis[2, 3], metric_3, halign = :left)
    Label(analysis[2, 4], metric_4, halign = :left)
    Label(analysis[3, 1:4], detail, halign = :left, color = MUTED)

    wave_time = Observable(Float64[])
    wave_x = Observable(Float64[])
    wave_y = Observable(Float64[])
    wave_cursor = Observable(Point2f[])
    wave_point_x = Observable(Point2f[])
    wave_point_y = Observable(Point2f[])
    trajectory_full = Observable(Point2f[])
    trajectory_trace = Observable(Point2f[])
    trajectory_colors = Observable(Float64[])
    current_point = Observable(Point2f[])
    arrow_points = Observable(Point2f[])
    major_axis_points = Observable(Point2f[])
    minor_axis_points = Observable(Point2f[])

    phase_metric_x = Observable(Float64[])
    phase_metric_y = Observable(Float64[])
    phase_metric_point = Observable(Point2f[])
    normalized_curve = Observable(Point2f[])
    normalized_point = Observable(Point2f[])
    closure_x = Observable(Float64[])
    closure_y = Observable(Float64[])
    closure_point = Observable(Point2f[])
    detune_x = Observable(Float64[])
    detune_y = Observable(Float64[])
    detune_point = Observable(Point2f[])

    lines!(wave_axis, wave_time, wave_x, color = ACCENT_X, linewidth = 2.3, label = "x(t)")
    lines!(wave_axis, wave_time, wave_y, color = ACCENT_Y, linewidth = 2.3, label = "y(t)")
    lines!(wave_axis, wave_cursor, color = (:white, 0.35), linewidth = 1.4, linestyle = :dash)
    scatter!(wave_axis, wave_point_x, color = ACCENT_X, markersize = 11)
    scatter!(wave_axis, wave_point_y, color = ACCENT_Y, markersize = 11)
    axislegend(wave_axis, position = :rt, framevisible = false)

    lines!(trajectory_axis, trajectory_full, color = (:white, 0.28), linewidth = 1.8)
    lines!(
        trajectory_axis,
        trajectory_trace,
        color = trajectory_colors,
        colormap = :plasma,
        colorrange = (0.0, 1.0),
        linewidth = 3.8,
    )
    lines!(trajectory_axis, major_axis_points, color = ACCENT_MAJOR, linewidth = 2)
    lines!(trajectory_axis, minor_axis_points, color = ACCENT_MINOR, linewidth = 2)
    lines!(trajectory_axis, arrow_points, color = ACCENT_Y, linewidth = 2.8)
    scatter!(
        trajectory_axis,
        current_point,
        color = ACCENT_Y,
        markersize = 14,
        strokecolor = :white,
        strokewidth = 1.3,
    )
    hlines!(trajectory_axis, [0.0], color = (:white, 0.10), linewidth = 1)
    vlines!(trajectory_axis, [0.0], color = (:white, 0.10), linewidth = 1)

    lines!(aux_phase_axis, phase_metric_x, phase_metric_y, color = ACCENT_X, linewidth = 2.5)
    scatter!(aux_phase_axis, phase_metric_point, color = ACCENT_Y, markersize = 13)
    lines!(aux_normal_axis, normalized_curve, color = ACCENT_MINOR, linewidth = 3)
    scatter!(aux_normal_axis, normalized_point, color = ACCENT_Y, markersize = 13)
    hlines!(aux_normal_axis, [0.0], color = (:white, 0.10))
    vlines!(aux_normal_axis, [0.0], color = (:white, 0.10))
    lines!(aux_ratio_axis, closure_x, closure_y, color = ACCENT_X, linewidth = 2.5)
    scatter!(aux_ratio_axis, closure_point, color = ACCENT_Y, markersize = 13)
    lines!(aux_detune_axis, detune_x, detune_y, color = ACCENT_MAJOR, linewidth = 2.5)
    scatter!(aux_detune_axis, detune_point, color = ACCENT_Y, markersize = 13)

    current_data = Ref{Any}()
    current_parameters = Ref{Any}()

    function parameters()
        return (
            amplitude_a = Float64(amplitude_a_slider.value[]),
            amplitude_b = Float64(amplitude_b_slider.value[]),
            frequency = Float64(frequency_slider.value[]),
            phase = deg2rad(Float64(phase_slider.value[])),
            m = Int(m_slider.value[]),
            n = Int(n_slider.value[]),
            delta_frequency = Float64(detune_slider.value[]),
            sample_count = Int(sample_slider.value[]),
        )
    end

    function update_auxiliary_visibility()
        for (key, axis) in auxiliary_axes
            visible = key == mode[]
            axis.blockscene.visible[] = visible
            axis.scene.visible[] = visible
        end

        show_b = mode[] == :amplitude
        for block in (amplitude_b_label, amplitude_b_slider, amplitude_b_value)
            set_block_visible!(block, show_b)
        end
        show_ratio = mode[] == :ratio
        for block in (m_label, m_slider, m_value, n_label, n_slider, n_value)
            set_block_visible!(block, show_ratio)
        end
        show_detune = mode[] == :detune
        for block in (detune_label, detune_slider, detune_value)
            set_block_visible!(block, show_detune)
        end

        if mode[] == :phase
            amplitude_a_label_text[] = "共同振幅 A"
            frequency_label_text[] = "共同频率 f"
            phase_label_text[] = "相位差 φ"
            progress_label_text[] = "质点进程"
            trajectory_title[] = "同频同振幅主轨迹"
        elseif mode[] == :amplitude
            amplitude_a_label_text[] = "X 振幅 A"
            frequency_label_text[] = "共同频率 f"
            phase_label_text[] = "相位差 φ"
            progress_label_text[] = "质点进程"
            trajectory_title[] = "不同振幅的原始轨迹"
        elseif mode[] == :ratio
            amplitude_a_label_text[] = "共同振幅 A"
            frequency_label_text[] = "基频 f₀"
            phase_label_text[] = "初相位 φ"
            progress_label_text[] = "闭合进程"
            trajectory_title[] = "有理频率比闭合轨迹"
        else
            amplitude_a_label_text[] = "共同振幅 A"
            frequency_label_text[] = "X 频率 f"
            phase_label_text[] = "初相位 φ₀"
            progress_label_text[] = "形变进程"
            trajectory_title[] = "最近一个周期的动态轨迹"
        end

        for (key, button) in mode_buttons
            button.buttoncolor[] = key == mode[] ? BUTTON_ACTIVE : BUTTON_BG
        end
        return nothing
    end

    function update_frame(progress_integer)
        p = current_parameters[]
        progress = progress_integer / 1000
        active_mode = mode[]
        data = current_data[]

        if active_mode == :detune
            data = detune_frame(
                p.amplitude_a,
                p.frequency,
                p.delta_frequency,
                p.phase,
                p.sample_count,
                progress,
            )
            current_data[] = data
            wave_time[] = data.time
            wave_x[] = data.x
            wave_y[] = data.y
            trajectory_full[] = data.trajectory
            trajectory_trace[] = data.trajectory
            trajectory_colors[] = time_colors(length(data.trajectory))
            index = length(data.time)
            current_t = data.current_time
            wave_cursor[] = Point2f[
                Point2f(current_t, -1.18 * p.amplitude_a),
                Point2f(current_t, 1.18 * p.amplitude_a),
            ]
            wave_point_x[] = Point2f[Point2f(current_t, data.x[index])]
            wave_point_y[] = Point2f[Point2f(current_t, data.y[index])]
            current_point[] = Point2f[data.trajectory[index]]
            arrow_points[] = direction_arrow(
                p.amplitude_a,
                p.amplitude_a,
                data.frequency_x,
                data.frequency_y,
                p.phase,
                current_t,
            )
            major_axis_points[] = Point2f[]
            minor_axis_points[] = Point2f[]

            animation_span =
                isfinite(data.shape_period) ? data.shape_period : 2 * inv(p.frequency)
            detune_x[] = data.phase_time ./ animation_span
            detune_y[] = data.unwrapped_cycles
            current_unwrapped = p.phase / TWO_PI + p.delta_frequency * current_t
            detune_point[] = Point2f[Point2f(progress, current_unwrapped)]
            xlims!(aux_detune_axis, 0.0, 1.0)
            y_margin = 0.15
            ylims!(
                aux_detune_axis,
                minimum(data.unwrapped_cycles) - y_margin,
                maximum(data.unwrapped_cycles) + y_margin,
            )
            limits!(
                wave_axis,
                first(data.time),
                last(data.time),
                -1.18 * p.amplitude_a,
                1.18 * p.amplitude_a,
            )
            metric_1[] = @sprintf("fx = %.2f Hz", data.frequency_x)
            metric_2[] = @sprintf("fy = %.2f Hz", data.frequency_y)
            metric_3[] = isfinite(data.shape_period) ?
                @sprintf("Tshape = %.3f s", data.shape_period) :
                "Tshape = ∞"
            metric_4[] = @sprintf("等效相位 = %.1f°", rad2deg(data.effective_phase))
            detail[] =
                "频率差使相位持续累积；形变进程走完一周时，相位累计改变 2π。"
        else
            index = clamp(
                round(Int, progress * (length(data.time) - 1)) + 1,
                1,
                length(data.time),
            )
            wave_time[] = data.time
            wave_x[] = data.x
            wave_y[] = data.y
            trajectory_full[] = data.trajectory
            trajectory_trace[] = data.trajectory[1:index]
            trajectory_colors[] = time_colors(index)
            current_t = data.time[index]
            amplitude_y = active_mode == :amplitude ? p.amplitude_b : p.amplitude_a
            margin = 1.18 * max(p.amplitude_a, amplitude_y)
            wave_cursor[] = Point2f[
                Point2f(current_t, -margin),
                Point2f(current_t, margin),
            ]
            wave_point_x[] = Point2f[Point2f(current_t, data.x[index])]
            wave_point_y[] = Point2f[Point2f(current_t, data.y[index])]
            current_point[] = Point2f[data.trajectory[index]]
            arrow_points[] = direction_arrow(
                p.amplitude_a,
                amplitude_y,
                data.frequency_x,
                data.frequency_y,
                p.phase,
                current_t,
            )
            limits!(wave_axis, first(data.time), last(data.time), -margin, margin)

            if active_mode == :phase
                phase_metric_point[] = Point2f[
                    Point2f(phase_slider.value[], data.semiaxes[2] / data.semiaxes[1]),
                ]
                metric_1[] = "形状：$(shape_name(p.phase))"
                metric_2[] = "方向：$(rotation_name(p.phase))"
                metric_3[] = @sprintf(
                    "半轴 a = %.4f，b = %.4f",
                    data.semiaxes[1],
                    data.semiaxes[2],
                )
                metric_4[] = @sprintf("方程残差 = %.2e", data.residual)
                conjugate_degree = mod(360 - phase_slider.value[], 360)
                detail[] =
                    "静态轨迹不能区分 φ = $(phase_slider.value[])° 与 φ = $(conjugate_degree)°；运动箭头可消除方向歧义。"
            elseif active_mode == :amplitude
                normalized_point[] = Point2f[data.normalized[index]]
                metric_1[] = @sprintf("振幅比 B/A = %.3f", p.amplitude_b / p.amplitude_a)
                metric_2[] = @sprintf(
                    "宽 = %.3f，高 = %.3f",
                    2 * p.amplitude_a,
                    2 * p.amplitude_b,
                )
                metric_3[] = @sprintf("椭圆面积 = %.4f", data.area)
                metric_4[] = @sprintf("归一化残差 = %.2e", data.residual)
                detail[] =
                    "原始轨迹的宽高随 B/A 改变；归一化后只保留相位关系。"
            else
                normalized_time = data.time ./ data.close_period
                closure_point[] = Point2f[
                    Point2f(normalized_time[index], data.closure_distance[index]),
                ]
                metric_1[] =
                    "频率比 $(p.m):$(p.n) → $(data.reduced_m):$(data.reduced_n)"
                metric_2[] = @sprintf(
                    "fx = %.2f Hz，fy = %.2f Hz",
                    data.frequency_x,
                    data.frequency_y,
                )
                metric_3[] = @sprintf("Tclose = %.4f s", data.close_period)
                metric_4[] = @sprintf("终点闭合误差 = %.2e", data.endpoint_error)
                detail[] =
                    progress >= 0.999 ?
                    "闭合完成：两个方向都回到各自的初始相位。" :
                    "彩色轨迹显示当前闭合进程；右图给出轨迹到起点的距离。"
            end
        end
        return nothing
    end

    function recompute()
        status[] = "正在计算..."
        yield()
        p = parameters()
        current_parameters[] = p
        active_mode = mode[]

        if active_mode == :phase
            data = phase_ellipse(
                p.amplitude_a,
                p.frequency,
                p.phase,
                p.sample_count,
            )
            phase_metric_x[] = data.phase_grid
            phase_metric_y[] = data.ratio_curve
            xlims!(aux_phase_axis, 0.0, 360.0)
            ylims!(aux_phase_axis, -0.05, 1.05)
            normalized_curve[] = Point2f[]
            closure_x[] = Float64[]
            closure_y[] = Float64[]
        elseif active_mode == :amplitude
            data = amplitude_ellipse(
                p.amplitude_a,
                p.amplitude_b,
                p.frequency,
                p.phase,
                p.sample_count,
            )
            normalized_curve[] = data.normalized
            limits!(aux_normal_axis, -1.15, 1.15, -1.15, 1.15)
            phase_metric_x[] = Float64[]
            phase_metric_y[] = Float64[]
            closure_x[] = Float64[]
            closure_y[] = Float64[]
        elseif active_mode == :ratio
            data = ratio_curve(
                p.amplitude_a,
                p.frequency,
                p.m,
                p.n,
                p.phase,
                p.sample_count,
            )
            closure_x[] = data.time ./ data.close_period
            closure_y[] = data.closure_distance
            xlims!(aux_ratio_axis, 0.0, 1.0)
            ylims!(
                aux_ratio_axis,
                -0.05,
                max(0.10, 1.08 * maximum(data.closure_distance)),
            )
            phase_metric_x[] = Float64[]
            phase_metric_y[] = Float64[]
            normalized_curve[] = Point2f[]
        else
            data = detune_frame(
                p.amplitude_a,
                p.frequency,
                p.delta_frequency,
                p.phase,
                p.sample_count,
                progress_slider.value[] / 1000,
            )
            phase_metric_x[] = Float64[]
            phase_metric_y[] = Float64[]
            normalized_curve[] = Point2f[]
            closure_x[] = Float64[]
            closure_y[] = Float64[]
        end

        current_data[] = data
        if active_mode in (:phase, :amplitude)
            major, minor = ellipse_axis_segments(data.semiaxes, data.directions)
            major_axis_points[] = major
            minor_axis_points[] = minor
        else
            major_axis_points[] = Point2f[]
            minor_axis_points[] = Point2f[]
        end
        amplitude_y = active_mode == :amplitude ? p.amplitude_b : p.amplitude_a
        margin = 1.18 * max(p.amplitude_a, amplitude_y)
        limits!(trajectory_axis, -margin, margin, -margin, margin)
        update_frame(progress_slider.value[])
        status[] = "就绪"
        return nothing
    end

    for (key, button) in mode_buttons
        on(button.clicks) do _
            playing[] = false
            mode[] = key
        end
    end

    on(mode) do _
        update_auxiliary_visibility()
        recompute()
    end

    onany(
        amplitude_a_slider.value,
        amplitude_b_slider.value,
        frequency_slider.value,
        phase_slider.value,
        m_slider.value,
        n_slider.value,
        detune_slider.value,
        sample_slider.value,
    ) do _...
        recompute()
    end

    on(progress_slider.value) do value
        update_frame(value)
    end

    on(play_button.clicks) do _
        playing[] = !playing[]
    end

    on(reset_button.clicks) do _
        playing[] = false
        set_close_to!(amplitude_a_slider, 1.0)
        set_close_to!(amplitude_b_slider, 0.65)
        set_close_to!(frequency_slider, 1.0)
        set_close_to!(phase_slider, 60)
        set_close_to!(m_slider, 2)
        set_close_to!(n_slider, 3)
        set_close_to!(detune_slider, 0.05)
        set_close_to!(sample_slider, 1000)
        set_close_to!(progress_slider, 0)
        set_close_to!(speed_slider, 0.5)
        status[] = "已重置"
    end

    output_dir = joinpath(LAB_DIR, "output")
    on(export_button.clicks) do _
        playing[] = false
        status[] = "正在导出..."
        yield()
        mkpath(output_dir)
        timestamp = Dates.format(now(), "yyyymmdd_HHMMSS")
        prefix = "lissajous_lab_$(MODE_FILES[mode[]])_$timestamp"
        png_path = joinpath(output_dir, "$prefix.png")
        csv_path = joinpath(output_dir, "$prefix.csv")
        try
            save(png_path, figure, px_per_unit = 1)
            write_csv(csv_path, mode[], current_parameters[], current_data[])
            status[] = "导出完成：output/$prefix"
        catch error
            status[] = "导出失败：$(sprint(showerror, error))"
        end
    end

    on(events(figure).tick) do tick
        if playing[]
            next_value = mod(
                progress_slider.value[] + tick.delta_time * speed_slider.value[] * 125,
                1001,
            )
            set_close_to!(progress_slider, round(Int, next_value))
        end
        return nothing
    end

    colsize!(figure.layout, 1, Relative(0.46))
    colsize!(figure.layout, 2, Relative(0.27))
    colsize!(figure.layout, 3, Relative(0.27))
    rowsize!(figure.layout, 1, 35)
    rowsize!(figure.layout, 2, 33)
    rowsize!(figure.layout, 3, 300)
    rowsize!(figure.layout, 4, 210)
    rowsize!(figure.layout, 5, 96)
    rowgap!(figure.layout, 6)

    colsize!(controls, 1, Relative(0.38))
    colsize!(controls, 2, Relative(0.34))
    colsize!(controls, 3, Relative(0.28))
    for grid in (basic_grid, special_grid, motion_grid)
        rowgap!(grid, 4)
    end
    for row in 1:4
        rowsize!(basic_grid, row, 27)
        rowsize!(special_grid, row, 27)
    end
    for column in 1:4
        colsize!(analysis, column, Relative(0.25))
    end

    update_auxiliary_visibility()
    recompute()
    state = (;
        mode,
        current_data,
        current_parameters,
        amplitude_a_slider,
        amplitude_b_slider,
        frequency_slider,
        phase_slider,
        m_slider,
        n_slider,
        detune_slider,
        sample_slider,
        progress_slider,
    )
    return figure, state
end

function run_model_tests()
    phase_data = phase_ellipse(1.0, 2.0, pi / 2, 1201)
    @assert isapprox(phase_data.semiaxes[1], 1.0; atol = 1.0e-10)
    @assert isapprox(phase_data.semiaxes[2], 1.0; atol = 1.0e-10)
    @assert phase_data.residual < 1.0e-10
    @assert rotation_name(pi / 2) == "顺时针"

    amplitude_data = amplitude_ellipse(1.0, 0.5, 1.0, pi / 3, 1201)
    @assert isapprox(amplitude_data.area, pi * 0.5 * sin(pi / 3); atol = 1.0e-10)
    @assert maximum(abs(point[1]) for point in amplitude_data.normalized) <= 1.0 + 1.0e-12
    @assert maximum(abs(point[2]) for point in amplitude_data.normalized) <= 1.0 + 1.0e-12

    ratio_data = ratio_curve(1.0, 2.0, 2, 4, pi / 5, 1601)
    @assert ratio_data.reduced_m == 1
    @assert ratio_data.reduced_n == 2
    @assert isapprox(ratio_data.close_period, 0.25; atol = 1.0e-12)
    @assert ratio_data.endpoint_error < 1.0e-10

    detune_data = detune_frame(1.0, 2.0, 0.10, pi / 6, 1201, 1.0)
    @assert isapprox(detune_data.shape_period, 10.0; atol = 1.0e-12)
    @assert isapprox(detune_data.effective_phase, pi / 6; atol = 1.0e-10)
    println("四模式模型自检通过：相位、振幅比、闭合周期和失谐周期均正常。")
end

function main()
    if "--self-test" in ARGS
        run_model_tests()
        return
    end

    figure, state = build_lab()
    if "--smoke-test" in ARGS
        output_dir = joinpath(LAB_DIR, "output")
        mkpath(output_dir)
        for key in MODE_ORDER
            state.mode[] = key
            if key == :amplitude
                set_close_to!(state.amplitude_b_slider, 0.75)
            elseif key == :ratio
                set_close_to!(state.m_slider, 3)
                set_close_to!(state.n_slider, 4)
            elseif key == :detune
                set_close_to!(state.detune_slider, -0.08)
            end
            set_close_to!(state.progress_slider, 625)
            @assert !isempty(state.current_data[].trajectory)
            smoke_path = joinpath(output_dir, "smoke_$(MODE_FILES[key]).png")
            save(smoke_path, figure, px_per_unit = 1)
        end
        state.mode[] = :phase
        set_close_to!(state.phase_slider, 60)
        set_close_to!(state.progress_slider, 720)
        output_path = joinpath(output_dir, "interface_preview.png")
        save(output_path, figure, px_per_unit = 1)
        csv_test_path = joinpath(output_dir, "smoke_export.csv")
        write_csv(csv_test_path, state.mode[], state.current_parameters[], state.current_data[])
        @assert isfile(csv_test_path)
        @assert countlines(csv_test_path) > state.current_parameters[].sample_count
        rm(csv_test_path; force = true)
        println("四模式界面冒烟测试通过：$output_path")
        return
    end

    screen = GLMakie.Screen()
    display(screen, figure)
    wait(screen)
end

main()
