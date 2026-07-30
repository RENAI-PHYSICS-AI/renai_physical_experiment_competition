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
using Random

GLMakie.activate!(title = "李萨如图形与声速测量")

const TWO_PI = 2pi
const MIC_1_POSITION = 0.12
const ACCENT_WAVE = RGBf(0.18, 0.78, 0.92)
const ACCENT_MIC_1 = RGBf(0.94, 0.35, 0.50)
const ACCENT_MIC_2 = RGBf(1.00, 0.72, 0.24)
const ACCENT_GOOD = RGBf(0.36, 0.82, 0.55)
const MUTED = RGBf(0.58, 0.62, 0.70)
const PANEL_BG = RGBf(0.075, 0.085, 0.105)
const BUTTON_BG = RGBf(0.13, 0.15, 0.19)
const BUTTON_ACTIVE = RGBf(0.15, 0.42, 0.58)

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

function time_colors(count)
    count <= 1 && return [0.0]
    return collect(range(0.0, 1.0; length = count))
end

function phase_projection(signal, time, angular_frequency)
    reference = cis.(-angular_frequency .* time)
    return sum(signal .* reference)
end

function simulate_signals(parameters, signal_mode, calibration_enabled)
    p = parameters
    angular_frequency = TWO_PI * p.frequency
    period = inv(p.frequency)
    time = collect(range(0.0, 2 * period; length = p.sample_count + 1))[1:end-1]
    mic_2_position = MIC_1_POSITION + p.distance
    physical_phase = angular_frequency * p.distance / p.sound_speed
    channel_phase = deg2rad(p.channel_phase_degree)
    observed_phase = physical_phase + channel_phase

    ideal_x = sin.(angular_frequency .* (time .- MIC_1_POSITION / p.sound_speed))
    ideal_y =
        p.amplitude_ratio .*
        sin.(angular_frequency .* (time .- mic_2_position / p.sound_speed) .- channel_phase)

    if signal_mode == :noisy
        rng = MersenneTwister(20260730)
        scale = 10.0^(p.snr_db / 20)
        noise_x = (inv(sqrt(2)) / scale) .* randn(rng, p.sample_count)
        noise_y =
            (p.amplitude_ratio / sqrt(2) / scale) .* randn(rng, p.sample_count)
        signal_x = ideal_x .+ noise_x
        signal_y = ideal_y .+ noise_y
    else
        signal_x = copy(ideal_x)
        signal_y = copy(ideal_y)
    end

    coefficient_x = phase_projection(signal_x, time, angular_frequency)
    coefficient_y = phase_projection(signal_y, time, angular_frequency)
    measured_phase = mod(angle(coefficient_x) - angle(coefficient_y), TWO_PI)
    calibration_phase = calibration_enabled ? channel_phase : 0.0
    corrected_wrapped_phase = mod(measured_phase - calibration_phase, TWO_PI)
    estimated_total_phase =
        TWO_PI * p.assumed_cycles + corrected_wrapped_phase

    estimated_speed =
        estimated_total_phase > 1.0e-10 ?
        TWO_PI * p.frequency * p.distance / estimated_total_phase :
        NaN
    wrapped_speed =
        measured_phase > 1.0e-10 ?
        TWO_PI * p.frequency * p.distance / measured_phase :
        NaN

    wavelength = p.sound_speed / p.frequency
    true_cycles = floor(Int, physical_phase / TWO_PI + 1.0e-10)
    time_delay = p.distance / p.sound_speed
    relative_error =
        isfinite(estimated_speed) ?
        (estimated_speed - p.sound_speed) / p.sound_speed :
        NaN

    return (;
        time,
        signal_x,
        signal_y,
        ideal_x,
        ideal_y,
        trajectory = Point2f.(signal_x, signal_y),
        ideal_trajectory = Point2f.(ideal_x, ideal_y),
        angular_frequency,
        period,
        mic_2_position,
        physical_phase,
        observed_phase,
        measured_phase,
        corrected_wrapped_phase,
        estimated_total_phase,
        wavelength,
        true_cycles,
        time_delay,
        estimated_speed,
        wrapped_speed,
        relative_error,
    )
end

function direction_arrow(parameters, time)
    p = parameters
    omega = TWO_PI * p.frequency
    channel_phase = deg2rad(p.channel_phase_degree)
    mic_2_position = MIC_1_POSITION + p.distance
    point = [
        sin(omega * (time - MIC_1_POSITION / p.sound_speed)),
        p.amplitude_ratio *
        sin(omega * (time - mic_2_position / p.sound_speed) - channel_phase),
    ]
    velocity = [
        omega * cos(omega * (time - MIC_1_POSITION / p.sound_speed)),
        omega * p.amplitude_ratio *
        cos(omega * (time - mic_2_position / p.sound_speed) - channel_phase),
    ]
    speed = norm(velocity)
    speed < 1.0e-10 && return Point2f[Point2f(point...)]

    direction = velocity ./ speed
    scale = max(1.0, p.amplitude_ratio)
    tip = point .+ 0.24 * scale .* direction
    angle = atan(direction[2], direction[1])
    head_length = 0.08 * scale
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

function write_csv(path, parameters, signal_mode, calibration_enabled, data)
    open(path, "w") do io
        println(io, "# experiment,李萨如图形与声速测量")
        println(io, "# signal_mode,$signal_mode")
        println(io, "# calibration_enabled,$calibration_enabled")
        for (key, value) in pairs(parameters)
            println(io, "# $(key),$(value)")
        end
        println(io, "# measured_phase_rad,$(data.measured_phase)")
        println(io, "# estimated_speed_m_s,$(data.estimated_speed)")
        println(io, "t_s,channel_x,channel_y,ideal_x,ideal_y")
        for i in eachindex(data.time)
            @printf(
                io,
                "%.10f,%.10f,%.10f,%.10f,%.10f\n",
                data.time[i],
                data.signal_x[i],
                data.signal_y[i],
                data.ideal_x[i],
                data.ideal_y[i],
            )
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
        "李萨如图形与声速测量：双麦克风相位法",
        fontsize = 25,
        font = :bold,
        halign = :left,
        color = :white,
    )

    signal_mode = Observable(:ideal)
    calibration_enabled = Observable(true)
    mode_grid = GridLayout()
    figure[2, 1:3] = mode_grid
    Label(mode_grid[1, 1], "信号模型", halign = :right, color = MUTED)
    ideal_button = Button(
        mode_grid[1, 2],
        label = "理想信号",
        height = 29,
        buttoncolor = BUTTON_ACTIVE,
        labelcolor = :white,
    )
    noisy_button = Button(
        mode_grid[1, 3],
        label = "加噪信号",
        height = 29,
        buttoncolor = BUTTON_BG,
        labelcolor = :white,
    )
    mode_summary = Observable("理想双通道信号；校准已开启")
    Label(mode_grid[1, 4], mode_summary, halign = :left, color = MUTED)

    space_axis = Axis(
        figure[3, 1],
        title = "声波传播与双麦克风位置",
        xlabel = "传播位置 x / m",
        ylabel = "瞬时位移",
    )
    time_axis = Axis(
        figure[3, 2],
        title = "两个麦克风的时域信号",
        xlabel = "时间 t / s",
        ylabel = "归一化电压",
    )
    lissajous_axis = Axis(
        figure[3, 3],
        title = "实时李萨如图形",
        xlabel = "M1 信号",
        ylabel = "M2 信号",
        aspect = DataAspect(),
    )

    controls = GridLayout()
    figure[4, 1:3] = controls
    Label(controls[1, 1:2], "实验参数", font = :bold, halign = :left, color = :white)
    geometry_grid = GridLayout()
    signal_grid = GridLayout()
    motion_grid = GridLayout()
    controls[2, 1] = geometry_grid
    controls[2, 2] = signal_grid
    controls[2, 3] = motion_grid

    frequency_slider = Slider(
        geometry_grid[1, 2],
        range = 200:10:2000,
        startvalue = 1000,
        update_while_dragging = false,
    )
    distance_slider = Slider(
        geometry_grid[2, 2],
        range = 0.05:0.01:1.50,
        startvalue = 0.50,
        update_while_dragging = false,
    )
    speed_slider = Slider(
        geometry_grid[3, 2],
        range = 300:1:380,
        startvalue = 343,
        update_while_dragging = false,
    )
    cycle_slider = Slider(
        geometry_grid[4, 2],
        range = 0:1:12,
        startvalue = 1,
        update_while_dragging = false,
    )
    Label(geometry_grid[1, 1], "声源频率 f", halign = :right)
    Label(geometry_grid[2, 1], "麦克风间距 d", halign = :right)
    Label(geometry_grid[3, 1], "设定声速 v", halign = :right)
    Label(geometry_grid[4, 1], "假设整周数 n", halign = :right)
    Label(geometry_grid[1, 3], lift(value -> "$(value) Hz", frequency_slider.value))
    Label(
        geometry_grid[2, 3],
        lift(value -> @sprintf("%.2f m", value), distance_slider.value),
    )
    Label(geometry_grid[3, 3], lift(value -> "$(value) m/s", speed_slider.value))
    Label(geometry_grid[4, 3], lift(string, cycle_slider.value))

    amplitude_slider = Slider(
        signal_grid[1, 2],
        range = 0.50:0.05:1.50,
        startvalue = 0.85,
        update_while_dragging = false,
    )
    channel_phase_slider = Slider(
        signal_grid[2, 2],
        range = -30:1:30,
        startvalue = 8,
        update_while_dragging = false,
    )
    snr_slider = Slider(
        signal_grid[3, 2],
        range = 10:1:60,
        startvalue = 30,
        update_while_dragging = false,
    )
    sample_slider = Slider(
        signal_grid[4, 2],
        range = 500:100:3000,
        startvalue = 1200,
        update_while_dragging = false,
    )
    Label(signal_grid[1, 1], "振幅比 B/A", halign = :right)
    Label(signal_grid[2, 1], "通道相位偏置", halign = :right)
    Label(signal_grid[3, 1], "信噪比 SNR", halign = :right)
    Label(signal_grid[4, 1], "采样点数 N", halign = :right)
    Label(
        signal_grid[1, 3],
        lift(value -> @sprintf("%.2f", value), amplitude_slider.value),
    )
    Label(signal_grid[2, 3], lift(value -> "$(value)°", channel_phase_slider.value))
    Label(signal_grid[3, 3], lift(value -> "$(value) dB", snr_slider.value))
    Label(signal_grid[4, 3], lift(string, sample_slider.value))

    progress_slider = Slider(
        motion_grid[1, 2],
        range = 0:1:1000,
        startvalue = 0,
        update_while_dragging = true,
    )
    animation_speed_slider = Slider(
        motion_grid[2, 2],
        range = 0.25:0.25:2.00,
        startvalue = 0.50,
        update_while_dragging = true,
    )
    Label(motion_grid[1, 1], "演示进程", halign = :right)
    Label(motion_grid[2, 1], "播放速度", halign = :right)
    Label(
        motion_grid[1, 3],
        lift(value -> @sprintf("%.1f%%", value / 10), progress_slider.value),
    )
    Label(
        motion_grid[2, 3],
        lift(value -> @sprintf("%.2f×", value), animation_speed_slider.value),
    )

    playing = Observable(false)
    play_label = lift(value -> value ? "暂停" : "播放", playing)
    calibration_label = lift(
        value -> value ? "校准：开" : "校准：关",
        calibration_enabled,
    )
    command_style = (
        height = 29,
        buttoncolor = BUTTON_BG,
        labelcolor = :white,
    )
    command_grid = GridLayout()
    motion_grid[3:5, 1:3] = command_grid
    play_button = Button(command_grid[1, 1]; label = play_label, command_style...)
    reset_button = Button(command_grid[1, 2]; label = "重置", command_style...)
    unwrap_button = Button(command_grid[2, 1]; label = "自动解包裹", command_style...)
    calibration_button = Button(
        command_grid[2, 2];
        label = calibration_label,
        command_style...,
    )
    export_button = Button(
        command_grid[3, 1:2];
        label = "导出 PNG + CSV",
        command_style...,
    )

    status = Observable("就绪")
    status_color = lift(text -> startswith(text, "正在") ? ACCENT_MIC_2 : ACCENT_GOOD, status)
    Label(controls[1, 3], status, color = status_color, halign = :right, font = :bold)

    analysis = GridLayout()
    figure[5, 1:3] = analysis
    Label(analysis[1, 1:4], "实时测量结果", font = :bold, halign = :left, color = :white)
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

    space_x = Observable(Float64[])
    space_wave = Observable(Float64[])
    source_point = Observable(Point2f[])
    microphone_points = Observable(Point2f[])
    microphone_guides = Observable(Point2f[])
    distance_bracket = Observable(Point2f[])
    microphone_label_positions = Observable(Point2f[])

    time_values = Observable(Float64[])
    time_signal_x = Observable(Float64[])
    time_signal_y = Observable(Float64[])
    time_cursor = Observable(Point2f[])
    time_point_x = Observable(Point2f[])
    time_point_y = Observable(Point2f[])

    ideal_trajectory = Observable(Point2f[])
    observed_trajectory = Observable(Point2f[])
    trace_trajectory = Observable(Point2f[])
    trace_colors = Observable(Float64[])
    current_point = Observable(Point2f[])
    arrow_points = Observable(Point2f[])

    lines!(space_axis, space_x, space_wave, color = ACCENT_WAVE, linewidth = 2.4)
    lines!(
        space_axis,
        microphone_guides,
        color = (:white, 0.22),
        linewidth = 1.2,
        linestyle = :dash,
    )
    lines!(space_axis, distance_bracket, color = ACCENT_MIC_2, linewidth = 2)
    scatter!(space_axis, source_point, color = ACCENT_WAVE, marker = :rect, markersize = 13)
    scatter!(
        space_axis,
        microphone_points,
        color = [ACCENT_MIC_1, ACCENT_MIC_2],
        markersize = 14,
        strokecolor = :white,
        strokewidth = 1,
    )
    text!(
        space_axis,
        microphone_label_positions,
        text = ["M1", "M2"],
        color = [ACCENT_MIC_1, ACCENT_MIC_2],
        align = (:center, :bottom),
        fontsize = 13,
    )

    lines!(time_axis, time_values, time_signal_x, color = ACCENT_MIC_1, linewidth = 2.2, label = "M1")
    lines!(time_axis, time_values, time_signal_y, color = ACCENT_MIC_2, linewidth = 2.2, label = "M2")
    lines!(time_axis, time_cursor, color = (:white, 0.35), linewidth = 1.3, linestyle = :dash)
    scatter!(time_axis, time_point_x, color = ACCENT_MIC_1, markersize = 11)
    scatter!(time_axis, time_point_y, color = ACCENT_MIC_2, markersize = 11)
    axislegend(time_axis, position = :rt, framevisible = false)

    ideal_plot = lines!(
        lissajous_axis,
        ideal_trajectory,
        color = (:white, 0.40),
        linewidth = 1.8,
        linestyle = :dash,
    )
    observed_line_plot = lines!(
        lissajous_axis,
        observed_trajectory,
        color = (:white, 0.25),
        linewidth = 1.5,
    )
    observed_scatter_plot = scatter!(
        lissajous_axis,
        observed_trajectory,
        color = (:white, 0.22),
        markersize = 3,
    )
    trace_line_plot = lines!(
        lissajous_axis,
        trace_trajectory,
        color = trace_colors,
        colormap = :plasma,
        colorrange = (0.0, 1.0),
        linewidth = 3.6,
    )
    trace_scatter_plot = scatter!(
        lissajous_axis,
        trace_trajectory,
        color = trace_colors,
        colormap = :plasma,
        colorrange = (0.0, 1.0),
        markersize = 4,
    )
    lines!(lissajous_axis, arrow_points, color = ACCENT_MIC_1, linewidth = 2.7)
    scatter!(
        lissajous_axis,
        current_point,
        color = ACCENT_MIC_1,
        markersize = 14,
        strokecolor = :white,
        strokewidth = 1.3,
    )
    hlines!(lissajous_axis, [0.0], color = (:white, 0.10), linewidth = 1)
    vlines!(lissajous_axis, [0.0], color = (:white, 0.10), linewidth = 1)

    current_data = Ref{Any}()
    current_parameters = Ref{Any}()

    function parameters()
        return (
            frequency = Float64(frequency_slider.value[]),
            distance = Float64(distance_slider.value[]),
            sound_speed = Float64(speed_slider.value[]),
            assumed_cycles = Int(cycle_slider.value[]),
            amplitude_ratio = Float64(amplitude_slider.value[]),
            channel_phase_degree = Float64(channel_phase_slider.value[]),
            snr_db = Float64(snr_slider.value[]),
            sample_count = Int(sample_slider.value[]),
        )
    end

    function update_analysis(data, p)
        metric_1[] = @sprintf(
            "λ = %.4f m，Δt = %.3f ms",
            data.wavelength,
            1000 * data.time_delay,
        )
        metric_2[] = @sprintf(
            "测得包裹相位 = %.2f°",
            rad2deg(data.measured_phase),
        )
        metric_3[] = "整周数：假设 $(p.assumed_cycles)，真实 $(data.true_cycles)"
        if isfinite(data.estimated_speed)
            metric_4[] = @sprintf(
                "测得声速 = %.2f m/s，误差 = %+.2f%%",
                data.estimated_speed,
                100 * data.relative_error,
            )
        else
            metric_4[] = "测得声速：相位不足，无法计算"
        end

        if p.assumed_cycles != data.true_cycles
            detail[] =
                "整数波长数选择错误：同一李萨如图形可对应相差若干个完整波长的距离。"
        elseif !calibration_enabled[] && abs(p.channel_phase_degree) > 0.5
            detail[] =
                "通道相位偏置尚未校准，测得相位同时包含传播相位和仪器相位。"
        elseif signal_mode[] == :noisy
            detail[] =
                @sprintf("已加入 %d dB 噪声；相位由双通道复数投影估计。", p.snr_db)
        else
            detail[] =
                "相位已校准并正确展开；拖动距离可观察图形每增加一个波长重复一次。"
        end
        return nothing
    end

    function update_frame(progress_integer)
        data = current_data[]
        p = current_parameters[]
        progress = progress_integer / 1000
        index = clamp(
            round(Int, progress * (length(data.time) - 1)) + 1,
            1,
            length(data.time),
        )
        current_time = data.time[index]
        amplitude_margin = 1.25 * max(1.0, p.amplitude_ratio)

        time_cursor[] = Point2f[
            Point2f(current_time, -amplitude_margin),
            Point2f(current_time, amplitude_margin),
        ]
        time_point_x[] = Point2f[Point2f(current_time, data.signal_x[index])]
        time_point_y[] = Point2f[Point2f(current_time, data.signal_y[index])]
        trace_trajectory[] = data.trajectory[1:index]
        trace_colors[] = time_colors(index)
        current_point[] = Point2f[data.trajectory[index]]
        arrow_points[] = direction_arrow(p, current_time)

        x_max = max(0.80, data.mic_2_position + 0.20)
        positions = collect(range(0.0, x_max; length = 1000))
        spatial = sin.(data.angular_frequency .* (current_time .- positions ./ p.sound_speed))
        space_x[] = positions
        space_wave[] = spatial
        bracket_y = -1.12 * amplitude_margin
        guide_top = 1.05 * amplitude_margin
        separator = Point2f(NaN, NaN)
        microphone_guides[] = Point2f[
            Point2f(MIC_1_POSITION, bracket_y),
            Point2f(MIC_1_POSITION, guide_top),
            separator,
            Point2f(data.mic_2_position, bracket_y),
            Point2f(data.mic_2_position, guide_top),
        ]
        tick_height = 0.07 * amplitude_margin
        distance_bracket[] = Point2f[
            Point2f(MIC_1_POSITION, bracket_y - tick_height),
            Point2f(MIC_1_POSITION, bracket_y + tick_height),
            separator,
            Point2f(MIC_1_POSITION, bracket_y),
            Point2f(data.mic_2_position, bracket_y),
            separator,
            Point2f(data.mic_2_position, bracket_y - tick_height),
            Point2f(data.mic_2_position, bracket_y + tick_height),
        ]
        source_point[] = Point2f[Point2f(0.0, spatial[1])]
        microphone_points[] = Point2f[
            Point2f(MIC_1_POSITION, data.signal_x[index]),
            Point2f(data.mic_2_position, data.signal_y[index]),
        ]
        microphone_label_positions[] = Point2f[
            Point2f(MIC_1_POSITION, guide_top),
            Point2f(data.mic_2_position, guide_top),
        ]
        limits!(space_axis, 0.0, x_max, -1.30 * amplitude_margin, 1.28 * amplitude_margin)
        return nothing
    end

    function recompute()
        status[] = "正在计算..."
        yield()
        p = parameters()
        data = simulate_signals(p, signal_mode[], calibration_enabled[])
        current_parameters[] = p
        current_data[] = data

        time_values[] = data.time
        time_signal_x[] = data.signal_x
        time_signal_y[] = data.signal_y
        ideal_trajectory[] = data.ideal_trajectory
        observed_trajectory[] = data.trajectory
        noisy = signal_mode[] == :noisy
        ideal_plot.visible[] = noisy
        observed_line_plot.visible[] = !noisy
        observed_scatter_plot.visible[] = noisy
        trace_line_plot.visible[] = !noisy
        trace_scatter_plot.visible[] = noisy

        amplitude_margin = 1.25 * max(1.0, p.amplitude_ratio)
        limits!(
            time_axis,
            first(data.time),
            last(data.time),
            -amplitude_margin,
            amplitude_margin,
        )
        limits!(
            lissajous_axis,
            -amplitude_margin,
            amplitude_margin,
            -amplitude_margin,
            amplitude_margin,
        )
        mode_summary[] =
            signal_mode[] == :ideal ?
            "理想双通道信号；校准$(calibration_enabled[] ? "已开启" : "已关闭")" :
            "加噪双通道信号；校准$(calibration_enabled[] ? "已开启" : "已关闭")"
        ideal_button.buttoncolor[] = signal_mode[] == :ideal ? BUTTON_ACTIVE : BUTTON_BG
        noisy_button.buttoncolor[] = signal_mode[] == :noisy ? BUTTON_ACTIVE : BUTTON_BG

        update_analysis(data, p)
        update_frame(progress_slider.value[])
        status[] = "就绪"
        return nothing
    end

    on(ideal_button.clicks) do _
        playing[] = false
        signal_mode[] = :ideal
    end
    on(noisy_button.clicks) do _
        playing[] = false
        signal_mode[] = :noisy
    end
    on(signal_mode) do _
        recompute()
    end
    on(calibration_enabled) do _
        recompute()
    end
    onany(
        frequency_slider.value,
        distance_slider.value,
        speed_slider.value,
        cycle_slider.value,
        amplitude_slider.value,
        channel_phase_slider.value,
        snr_slider.value,
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
    on(calibration_button.clicks) do _
        calibration_enabled[] = !calibration_enabled[]
    end
    on(unwrap_button.clicks) do _
        set_close_to!(cycle_slider, current_data[].true_cycles)
        status[] = "已按真实整周数展开相位"
    end
    on(reset_button.clicks) do _
        playing[] = false
        signal_mode[] = :ideal
        calibration_enabled[] = true
        set_close_to!(frequency_slider, 1000)
        set_close_to!(distance_slider, 0.50)
        set_close_to!(speed_slider, 343)
        set_close_to!(cycle_slider, 1)
        set_close_to!(amplitude_slider, 0.85)
        set_close_to!(channel_phase_slider, 8)
        set_close_to!(snr_slider, 30)
        set_close_to!(sample_slider, 1200)
        set_close_to!(progress_slider, 0)
        set_close_to!(animation_speed_slider, 0.5)
        status[] = "已重置"
    end

    output_dir = joinpath(LAB_DIR, "output")
    on(export_button.clicks) do _
        playing[] = false
        status[] = "正在导出..."
        yield()
        mkpath(output_dir)
        timestamp = Dates.format(now(), "yyyymmdd_HHMMSS")
        prefix = "lissajous_sound_speed_$timestamp"
        png_path = joinpath(output_dir, "$prefix.png")
        csv_path = joinpath(output_dir, "$prefix.csv")
        try
            save(png_path, figure, px_per_unit = 1)
            write_csv(
                csv_path,
                current_parameters[],
                signal_mode[],
                calibration_enabled[],
                current_data[],
            )
            status[] = "导出完成：output/$prefix"
        catch error
            status[] = "导出失败：$(sprint(showerror, error))"
        end
    end

    on(events(figure).tick) do tick
        if playing[]
            next_value = mod(
                progress_slider.value[] +
                tick.delta_time * animation_speed_slider.value[] * 250,
                1001,
            )
            set_close_to!(progress_slider, round(Int, next_value))
        end
        return nothing
    end

    colsize!(figure.layout, 1, Relative(0.36))
    colsize!(figure.layout, 2, Relative(0.36))
    colsize!(figure.layout, 3, Relative(0.28))
    rowsize!(figure.layout, 1, 35)
    rowsize!(figure.layout, 2, 32)
    rowsize!(figure.layout, 3, 300)
    rowsize!(figure.layout, 4, 215)
    rowsize!(figure.layout, 5, 100)
    rowgap!(figure.layout, 6)

    colsize!(controls, 1, Relative(0.37))
    colsize!(controls, 2, Relative(0.35))
    colsize!(controls, 3, Relative(0.28))
    for grid in (geometry_grid, signal_grid, motion_grid)
        rowgap!(grid, 4)
    end
    for row in 1:4
        rowsize!(geometry_grid, row, 27)
        rowsize!(signal_grid, row, 27)
    end
    for column in 1:4
        colsize!(analysis, column, Relative(0.25))
    end

    recompute()
    state = (;
        signal_mode,
        calibration_enabled,
        current_data,
        current_parameters,
        frequency_slider,
        distance_slider,
        speed_slider,
        cycle_slider,
        amplitude_slider,
        channel_phase_slider,
        snr_slider,
        sample_slider,
        progress_slider,
    )
    return figure, state
end

function run_model_tests()
    parameters = (
        frequency = 1000.0,
        distance = 0.50,
        sound_speed = 343.0,
        assumed_cycles = 1,
        amplitude_ratio = 0.85,
        channel_phase_degree = 8.0,
        snr_db = 30.0,
        sample_count = 1200,
    )
    ideal = simulate_signals(parameters, :ideal, true)
    @assert ideal.true_cycles == 1
    @assert isapprox(ideal.estimated_speed, 343.0; atol = 1.0e-8)

    uncalibrated = simulate_signals(parameters, :ideal, false)
    @assert abs(uncalibrated.estimated_speed - 343.0) > 1.0

    shifted_parameters = merge(
        parameters,
        (distance = parameters.distance + ideal.wavelength, assumed_cycles = 2),
    )
    shifted = simulate_signals(shifted_parameters, :ideal, true)
    @assert isapprox(shifted.estimated_speed, 343.0; atol = 1.0e-8)
    @assert maximum(
        norm(ideal.ideal_trajectory[i] - shifted.ideal_trajectory[i])
        for i in eachindex(ideal.ideal_trajectory)
    ) < 1.0e-10

    noisy = simulate_signals(parameters, :noisy, true)
    @assert isfinite(noisy.estimated_speed)
    @assert abs(noisy.estimated_speed - 343.0) < 5.0
    println("模型自检通过：校准、整周相位展开、波长周期性和噪声估计均正常。")
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
        set_close_to!(state.progress_slider, 680)
        state.signal_mode[] = :noisy
        set_close_to!(state.snr_slider, 24)
        @assert !isempty(state.current_data[].trajectory)
        noisy_path = joinpath(output_dir, "smoke_noisy.png")
        save(noisy_path, figure, px_per_unit = 1)

        state.signal_mode[] = :ideal
        set_close_to!(state.snr_slider, 30)
        state.calibration_enabled[] = false
        @assert abs(state.current_data[].estimated_speed - state.current_parameters[].sound_speed) > 1.0
        state.calibration_enabled[] = true
        set_close_to!(state.cycle_slider, state.current_data[].true_cycles)
        set_close_to!(state.progress_slider, 720)
        preview_path = joinpath(output_dir, "interface_preview.png")
        save(preview_path, figure, px_per_unit = 1)

        csv_path = joinpath(output_dir, "smoke_export.csv")
        write_csv(
            csv_path,
            state.current_parameters[],
            state.signal_mode[],
            state.calibration_enabled[],
            state.current_data[],
        )
        @assert isfile(csv_path)
        @assert countlines(csv_path) > state.current_parameters[].sample_count
        rm(csv_path; force = true)
        println("界面与导出冒烟测试通过：$preview_path")
        return
    end

    screen = GLMakie.Screen()
    display(screen, figure)
    wait(screen)
end

main()
