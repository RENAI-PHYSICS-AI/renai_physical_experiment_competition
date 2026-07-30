import Pkg

const LAB_DIR = @__DIR__
Pkg.activate(LAB_DIR)

if !("--no-instantiate" in ARGS)
    Pkg.instantiate()
end

using Dates
using DelimitedFiles
using GLMakie
using LinearAlgebra
using Printf

GLMakie.activate!(title = "李萨如图形实验一：相位差")

const TWO_PI = 2pi
const ACCENT_X = RGBf(0.18, 0.78, 0.92)
const ACCENT_Y = RGBf(0.94, 0.35, 0.50)
const ACCENT_MAJOR = RGBf(1.00, 0.72, 0.24)
const ACCENT_MINOR = RGBf(0.36, 0.82, 0.55)
const MUTED = RGBf(0.55, 0.60, 0.68)
const PANEL_BG = RGBf(0.075, 0.085, 0.105)

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
    bold = something(findfirst(isfile, bold_candidates), 0)
    bold_path = bold == 0 ? regular : bold_candidates[bold]
    return (; regular, bold = bold_path)
end

struct LabData
    time::Vector{Float64}
    x::Vector{Float64}
    y::Vector{Float64}
    theta::Vector{Float64}
    trajectory::Vector{Point2f}
    semiaxes::Vector{Float64}
    directions::Matrix{Float64}
    residual::Float64
end

function calculate_lab_data(amplitude, frequency, phase, sample_count)
    period = inv(frequency)
    time = collect(range(0.0, period; length = sample_count))
    theta = TWO_PI .* frequency .* time
    x = amplitude .* sin.(theta)
    y = amplitude .* sin.(theta .+ phase)
    trajectory = Point2f.(x, y)

    # [x, y]' = M * [sin(theta), cos(theta)]' maps the unit circle to the ellipse.
    map_matrix = amplitude .* [1.0 0.0; cos(phase) sin(phase)]
    factor = svd(map_matrix)
    semiaxes = collect(factor.S)
    directions = Matrix(factor.U)

    implicit_value = x .^ 2 .+ y .^ 2 .- 2 .* x .* y .* cos(phase)
    target = amplitude^2 * sin(phase)^2
    residual = maximum(abs.(implicit_value .- target))

    return LabData(
        time,
        x,
        y,
        theta,
        trajectory,
        semiaxes,
        directions,
        residual,
    )
end

function shape_name(phase; atol = deg2rad(0.5))
    wrapped = mod(phase, TWO_PI)
    if min(wrapped, TWO_PI - wrapped) <= atol
        return "正斜率直线  y = x"
    elseif abs(wrapped - pi) <= atol
        return "负斜率直线  y = -x"
    elseif abs(abs(sin(wrapped)) - 1.0) <= sin(atol)
        return "圆"
    end
    return "椭圆"
end

function rotation_name(phase)
    s = sin(phase)
    if abs(s) < 1.0e-8
        return "往复运动（方向在端点反转）"
    elseif s > 0
        return "顺时针"
    end
    return "逆时针"
end

function axis_segments(data::LabData)
    major = data.semiaxes[1] .* data.directions[:, 1]
    minor = data.semiaxes[2] .* data.directions[:, 2]
    separator = Point2f(NaN, NaN)
    major_points = Point2f[
        Point2f(-major[1], -major[2]),
        Point2f(major[1], major[2]),
    ]
    minor_points = Point2f[
        Point2f(-minor[1], -minor[2]),
        Point2f(minor[1], minor[2]),
    ]
    return major_points, minor_points
end

function direction_arrow(amplitude, phase, theta)
    point = [amplitude * sin(theta), amplitude * sin(theta + phase)]
    velocity = [cos(theta), cos(theta + phase)]
    speed = norm(velocity)
    if speed < 1.0e-10
        return Point2f[Point2f(point...)]
    end

    direction = velocity ./ speed
    arrow_length = max(0.16, 0.28 * amplitude)
    tip = point .+ arrow_length .* direction
    angle = atan(direction[2], direction[1])
    head_length = 0.09 * max(amplitude, 0.6)
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

function write_csv(path, data::LabData)
    open(path, "w") do io
        println(io, "t_s,x,y,theta_rad")
        for i in eachindex(data.time)
            @printf(
                io,
                "%.10f,%.10f,%.10f,%.10f\n",
                data.time[i],
                data.x[i],
                data.y[i],
                data.theta[i],
            )
        end
    end
end

function build_lab()
    lab_fonts = cjk_font_family()
    set_theme!(
        theme_dark();
        fontsize = 16,
        fonts = lab_fonts,
        backgroundcolor = RGBf(0.045, 0.050, 0.065),
        Axis = (
            backgroundcolor = PANEL_BG,
            xgridcolor = (:white, 0.08),
            ygridcolor = (:white, 0.08),
            titlecolor = RGBf(0.82, 0.84, 0.88),
            topspinevisible = false,
            rightspinevisible = false,
        ),
    )

    figure = Figure(size = (1360, 820), figure_padding = 16)
    Label(
        figure[1, 1:2],
        "实验一：相同频率下相位差对李萨如图形的影响",
        fontsize = 28,
        font = :bold,
        halign = :left,
        color = :white,
    )
    Label(
        figure[2, 1:2],
        "拖动相位差并播放质点运动，对照时域错位、轨迹形状、主轴和运动方向。",
        fontsize = 15,
        halign = :left,
        color = MUTED,
    )

    wave_axis = Axis(
        figure[3, 1],
        title = "X、Y 方向时域波形",
        xlabel = "时间 t / s",
        ylabel = "位移",
    )
    trajectory_axis = Axis(
        figure[3, 2],
        title = "李萨如轨迹与理论主轴",
        xlabel = "x",
        ylabel = "y",
        aspect = DataAspect(),
    )

    controls = GridLayout()
    figure[4, 1:2] = controls
    Label(controls[1, 1:4], "实验参数", font = :bold, halign = :left, color = :white)

    amplitude_slider = Slider(
        controls[2, 2],
        range = 0.20:0.05:2.00,
        startvalue = 1.00,
        update_while_dragging = false,
    )
    frequency_slider = Slider(
        controls[3, 2],
        range = 0.50:0.10:5.00,
        startvalue = 1.00,
        update_while_dragging = false,
    )
    phase_slider = Slider(
        controls[4, 2],
        range = 0:1:360,
        startvalue = 60,
        update_while_dragging = false,
    )
    sample_slider = Slider(
        controls[5, 2],
        range = 200:100:2000,
        startvalue = 1000,
        update_while_dragging = false,
    )
    motion_slider = Slider(
        controls[6, 2],
        range = 0:1:360,
        startvalue = 0,
        update_while_dragging = true,
    )
    speed_slider = Slider(
        controls[7, 2],
        range = 0.25:0.25:2.00,
        startvalue = 0.50,
        update_while_dragging = true,
    )

    Label(controls[2, 1], "振幅 A", halign = :right)
    Label(controls[3, 1], "频率 f", halign = :right)
    Label(controls[4, 1], "相位差 φ", halign = :right)
    Label(controls[5, 1], "采样点数 N", halign = :right)
    Label(controls[6, 1], "质点相角 θ", halign = :right)
    Label(controls[7, 1], "播放速度", halign = :right)

    Label(
        controls[2, 3],
        lift(value -> @sprintf("%.2f", value), amplitude_slider.value),
        halign = :left,
    )
    Label(
        controls[3, 3],
        lift(value -> @sprintf("%.2f Hz", value), frequency_slider.value),
        halign = :left,
    )
    Label(
        controls[4, 3],
        lift(value -> @sprintf("%d°  (%.3f rad)", value, deg2rad(value)), phase_slider.value),
        halign = :left,
    )
    Label(
        controls[5, 3],
        lift(value -> string(value), sample_slider.value),
        halign = :left,
    )
    Label(
        controls[6, 3],
        lift(value -> @sprintf("%d°", value), motion_slider.value),
        halign = :left,
    )
    Label(
        controls[7, 3],
        lift(value -> @sprintf("%.2f×", value), speed_slider.value),
        halign = :left,
    )

    status = Observable("就绪")
    status_color = lift(text -> startswith(text, "正在") ? ACCENT_MAJOR : ACCENT_MINOR, status)
    Label(controls[1, 4], status, color = status_color, halign = :right, font = :bold)

    phase_presets = [0, 45, 90, 135, 180, 270]
    preset_grid = GridLayout()
    controls[2:4, 4] = preset_grid
    Label(preset_grid[1, 1:3], "典型相位", color = MUTED)
    preset_buttons = Button[]
    for (index, phase_degree) in enumerate(phase_presets)
        row = 1 + cld(index, 3)
        column = mod1(index, 3)
        button = Button(
            preset_grid[row, column],
            label = "$(phase_degree)°",
            width = 72,
            height = 28,
            buttoncolor = RGBf(0.13, 0.15, 0.19),
            labelcolor = :white,
        )
        push!(preset_buttons, button)
    end

    playing = Observable(false)
    play_label = lift(value -> value ? "暂停" : "播放", playing)
    command_button_style = (
        height = 30,
        buttoncolor = RGBf(0.13, 0.15, 0.19),
        labelcolor = :white,
    )
    play_button = Button(controls[5, 4]; label = play_label, command_button_style...)
    reset_button = Button(controls[6, 4]; label = "重置", command_button_style...)
    export_button = Button(
        controls[7, 4];
        label = "导出 PNG + CSV",
        command_button_style...,
    )

    analysis = GridLayout()
    figure[5, 1:2] = analysis
    Label(analysis[1, 1:4], "实时分析", font = :bold, halign = :left, color = :white)
    shape_text = Observable("")
    direction_text = Observable("")
    axes_text = Observable("")
    residual_text = Observable("")
    ambiguity_text = Observable("")
    Label(analysis[2, 1], shape_text, halign = :left)
    Label(analysis[2, 2], direction_text, halign = :left)
    Label(analysis[2, 3], axes_text, halign = :left)
    Label(analysis[2, 4], residual_text, halign = :left)
    Label(analysis[3, 1:4], ambiguity_text, halign = :left, color = MUTED)

    time_data = Observable(Float64[])
    x_data = Observable(Float64[])
    y_data = Observable(Float64[])
    trajectory_data = Observable(Point2f[])
    trace_data = Observable(Point2f[])
    current_time_x = Observable(Point2f[])
    current_time_y = Observable(Point2f[])
    cursor_line = Observable(Point2f[])
    current_point = Observable(Point2f[])
    major_axis = Observable(Point2f[])
    minor_axis = Observable(Point2f[])
    arrow_data = Observable(Point2f[])
    current_lab_data = Ref{LabData}()

    lines!(wave_axis, time_data, x_data, color = ACCENT_X, linewidth = 2.5, label = "x(t)")
    lines!(wave_axis, time_data, y_data, color = ACCENT_Y, linewidth = 2.5, label = "y(t)")
    lines!(wave_axis, cursor_line, color = (:white, 0.35), linewidth = 1.5, linestyle = :dash)
    scatter!(wave_axis, current_time_x, color = ACCENT_X, markersize = 13)
    scatter!(wave_axis, current_time_y, color = ACCENT_Y, markersize = 13)
    axislegend(wave_axis, position = :rt, framevisible = false)

    lines!(
        trajectory_axis,
        trajectory_data,
        color = (:white, 0.28),
        linewidth = 2,
        label = "完整轨迹",
    )
    lines!(trajectory_axis, trace_data, color = ACCENT_X, linewidth = 4, label = "已运动轨迹")
    lines!(trajectory_axis, major_axis, color = ACCENT_MAJOR, linewidth = 2.5, label = "长轴")
    lines!(trajectory_axis, minor_axis, color = ACCENT_MINOR, linewidth = 2.5, label = "短轴")
    lines!(trajectory_axis, arrow_data, color = ACCENT_Y, linewidth = 3)
    scatter!(
        trajectory_axis,
        current_point,
        color = ACCENT_Y,
        markersize = 16,
        strokecolor = :white,
        strokewidth = 1.5,
    )
    hlines!(trajectory_axis, [0.0], color = (:white, 0.12), linewidth = 1)
    vlines!(trajectory_axis, [0.0], color = (:white, 0.12), linewidth = 1)
    axislegend(trajectory_axis, position = :rt, framevisible = false)

    function update_cursor(theta_value)
        data = current_lab_data[]
        amplitude = amplitude_slider.value[]
        frequency = frequency_slider.value[]
        phase = deg2rad(phase_slider.value[])

        sample_index = clamp(
            round(Int, theta_value / TWO_PI * (length(data.theta) - 1)) + 1,
            1,
            length(data.theta),
        )
        point = Point2f(
            amplitude * sin(theta_value),
            amplitude * sin(theta_value + phase),
        )
        t_current = theta_value / (TWO_PI * frequency)
        margin = 1.18 * amplitude

        trace_data[] = data.trajectory[1:sample_index]
        current_point[] = Point2f[point]
        current_time_x[] = Point2f[Point2f(t_current, point[1])]
        current_time_y[] = Point2f[Point2f(t_current, point[2])]
        cursor_line[] = Point2f[
            Point2f(t_current, -margin),
            Point2f(t_current, margin),
        ]
        arrow_data[] = direction_arrow(amplitude, phase, theta_value)
        return nothing
    end

    function recompute()
        status[] = "正在计算..."
        yield()

        amplitude = Float64(amplitude_slider.value[])
        frequency = Float64(frequency_slider.value[])
        phase = deg2rad(Float64(phase_slider.value[]))
        sample_count = Int(sample_slider.value[])
        data = calculate_lab_data(amplitude, frequency, phase, sample_count)
        current_lab_data[] = data

        time_data[] = data.time
        x_data[] = data.x
        y_data[] = data.y
        trajectory_data[] = data.trajectory
        major, minor = axis_segments(data)
        major_axis[] = major
        minor_axis[] = minor

        period = inv(frequency)
        margin = 1.18 * amplitude
        limits!(wave_axis, 0.0, period, -margin, margin)
        limits!(trajectory_axis, -margin, margin, -margin, margin)

        shape_text[] = "形状：$(shape_name(phase))"
        direction_text[] = "运动方向：$(rotation_name(phase))"
        axes_text[] = @sprintf(
            "理论半轴：a = %.4f，b = %.4f",
            data.semiaxes[1],
            data.semiaxes[2],
        )
        residual_text[] = @sprintf("方程最大残差：%.2e", data.residual)
        conjugate_degree = mod(360 - phase_slider.value[], 360)
        ambiguity_text[] =
            "静态轨迹不能区分 φ = $(phase_slider.value[])° 与 φ = $(conjugate_degree)°；运动箭头可消除这一方向歧义。"

        update_cursor(deg2rad(motion_slider.value[]))
        status[] = "就绪"
        return nothing
    end

    onany(
        amplitude_slider.value,
        frequency_slider.value,
        phase_slider.value,
        sample_slider.value,
    ) do _...
        recompute()
    end

    on(motion_slider.value) do degree
        update_cursor(deg2rad(degree))
    end

    for (button, phase_degree) in zip(preset_buttons, phase_presets)
        on(button.clicks) do _
            set_close_to!(phase_slider, phase_degree)
        end
    end

    on(play_button.clicks) do _
        playing[] = !playing[]
    end

    on(reset_button.clicks) do _
        playing[] = false
        set_close_to!(amplitude_slider, 1.0)
        set_close_to!(frequency_slider, 1.0)
        set_close_to!(phase_slider, 60)
        set_close_to!(sample_slider, 1000)
        set_close_to!(motion_slider, 0)
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
        png_path = joinpath(output_dir, "lissajous_phase_$timestamp.png")
        csv_path = joinpath(output_dir, "lissajous_phase_$timestamp.csv")
        try
            save(png_path, figure, px_per_unit = 1)
            write_csv(csv_path, current_lab_data[])
            status[] = "导出完成：output/$timestamp"
        catch error
            status[] = "导出失败：$(sprint(showerror, error))"
        end
    end

    on(events(figure).tick) do tick
        if playing[]
            next_degree = mod(
                motion_slider.value[] + tick.delta_time * speed_slider.value[] * 360,
                360,
            )
            set_close_to!(motion_slider, round(Int, next_degree))
        end
        return nothing
    end

    colsize!(figure.layout, 1, Relative(0.54))
    colsize!(figure.layout, 2, Relative(0.46))
    rowsize!(figure.layout, 1, 40)
    rowsize!(figure.layout, 2, 25)
    rowsize!(figure.layout, 3, 330)
    rowsize!(figure.layout, 4, 210)
    rowsize!(figure.layout, 5, 100)
    rowgap!(figure.layout, 6)
    colsize!(controls, 1, 110)
    colsize!(controls, 2, Auto(1))
    colsize!(controls, 3, 170)
    colsize!(controls, 4, 290)
    rowsize!(controls, 1, 22)
    for row in 2:7
        rowsize!(controls, row, 27)
    end
    rowgap!(controls, 4)
    for column in 1:4
        colsize!(analysis, column, Relative(0.25))
    end

    recompute()
    state = (;
        current_lab_data,
        amplitude_slider,
        frequency_slider,
        phase_slider,
        sample_slider,
        motion_slider,
        speed_slider,
    )
    return figure, state
end

function run_model_tests()
    for degree in (0, 30, 60, 90, 135, 180, 270, 360)
        data = calculate_lab_data(1.0, 2.0, deg2rad(degree), 2001)
        @assert data.residual < 1.0e-10
        @assert data.semiaxes[1] + 1.0e-12 >= data.semiaxes[2]
    end
    @assert shape_name(0.0) == "正斜率直线  y = x"
    @assert shape_name(pi / 2) == "圆"
    @assert shape_name(pi) == "负斜率直线  y = -x"
    @assert rotation_name(pi / 2) == "顺时针"
    @assert rotation_name(3pi / 2) == "逆时针"
    println("模型自检通过：特殊相位、旋转方向、半轴和隐式方程残差均正常。")
end

function main()
    if "--self-test" in ARGS
        run_model_tests()
        return
    end

    figure, state = build_lab()
    if "--smoke-test" in ARGS
        set_close_to!(state.phase_slider, 90)
        @assert isapprox(state.current_lab_data[].semiaxes[1], 1.0; atol = 1.0e-10)
        @assert isapprox(state.current_lab_data[].semiaxes[2], 1.0; atol = 1.0e-10)
        set_close_to!(state.motion_slider, 125)
        set_close_to!(state.phase_slider, 60)
        output_dir = joinpath(LAB_DIR, "output")
        mkpath(output_dir)
        output_path = joinpath(output_dir, "interface_preview.png")
        save(output_path, figure, px_per_unit = 1)
        println("界面冒烟测试通过：$output_path")
        return
    end

    screen = GLMakie.Screen()
    display(screen, figure)
    wait(screen)
end

main()
