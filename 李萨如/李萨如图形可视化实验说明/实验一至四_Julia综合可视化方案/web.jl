const LAB_DIR = @__DIR__
if abspath(PROGRAM_FILE) == @__FILE__
    import Pkg
    Pkg.activate(LAB_DIR)
    if !("--no-instantiate" in ARGS)
        Pkg.instantiate()
    end
end

using Bonito
using Dates
using LinearAlgebra
using Printf
using WGLMakie

const TWO_PI = 2pi
const ACCENT_X = RGBf(0.18, 0.78, 0.92)
const ACCENT_Y = RGBf(0.94, 0.35, 0.50)
const ACCENT_MAJOR = RGBf(1.00, 0.72, 0.24)
const ACCENT_MINOR = RGBf(0.36, 0.82, 0.55)
const PANEL_BG = RGBf(0.075, 0.085, 0.105)
const MUTED = RGBf(0.58, 0.62, 0.70)
const BUTTON_BG = RGBf(0.13, 0.15, 0.19)
const WGL_SHADER_FILES = (
    "mesh.frag",
    "mesh.vert",
    "particles.vert",
    "sprites.frag",
    "sprites.vert",
    "volume.frag",
    "volume.vert",
    "voxel.frag",
    "voxel.vert",
)

function load_packaged_wgl_shaders!()
    asset_dir = normpath(
        joinpath(Sys.BINDIR, "..", "share", "lissajous", "wglmakie_assets"),
    )
    isdir(asset_dir) || return false
    for name in WGL_SHADER_FILES
        path = joinpath(asset_dir, name)
        isfile(path) || error("缺少 WGLMakie 着色器文件：$(path)")
        WGLMakie.ALL_SHADERS[name] = read(path, String)
    end
    println("已从便携运行时加载 WGLMakie 着色器：$(asset_dir)")
    return true
end

function first_existing_font(candidates)
    for candidate in candidates
        isfile(candidate) && return candidate
    end
    return nothing
end

function configure_theme!()
    app_font = normpath(
        joinpath(
            Sys.BINDIR,
            "..",
            "share",
            "lissajous",
            "fonts",
            "NotoSansCJKsc-Regular.otf",
        ),
    )
    regular = first_existing_font([
        app_font,
        raw"C:\Windows\Fonts\msyh.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ])
    bold = first_existing_font([
        app_font,
        raw"C:\Windows\Fonts\msyhbd.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ])
    font_settings = if isnothing(regular)
        NamedTuple()
    else
        isnothing(bold) && (bold = regular)
        (; fonts = (; regular, bold))
    end
    set_theme!(
        theme_dark();
        font_settings...,
        fontsize = 15,
        backgroundcolor = RGBf(0.045, 0.050, 0.065),
        Axis = (
            backgroundcolor = PANEL_BG,
            xgridcolor = (:white, 0.08),
            ygridcolor = (:white, 0.08),
            topspinevisible = false,
            rightspinevisible = false,
        ),
    )
end

function ellipse_geometry(amplitude_x, amplitude_y, phase)
    matrix = [
        amplitude_x 0.0
        amplitude_y * cos(phase) amplitude_y * sin(phase)
    ]
    factor = svd(matrix)
    return collect(factor.S), Matrix(factor.U)
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
    abs(sin(phase)) < 1.0e-8 && return "往复运动"
    return sin(phase) > 0 ? "顺时针" : "逆时针"
end

function base_layout(title, auxiliary_title, auxiliary_x, auxiliary_y)
    figure = Figure(size = (960, 760), figure_padding = 20)
    Label(
        figure[1, 1:3],
        title,
        fontsize = 25,
        font = :bold,
        halign = :left,
        color = :white,
    )
    wave_axis = Axis(
        figure[2, 1],
        title = "X、Y 方向时域波形",
        xlabel = "归一化时间",
        ylabel = "位移",
    )
    trajectory_axis = Axis(
        figure[2, 2],
        title = "李萨如轨迹",
        xlabel = "x",
        ylabel = "y",
        aspect = DataAspect(),
    )
    auxiliary_axis = Axis(
        figure[2, 3],
        title = auxiliary_title,
        xlabel = auxiliary_x,
        ylabel = auxiliary_y,
    )
    controls = GridLayout()
    analysis = GridLayout()
    figure[3, 1:3] = controls
    figure[4, 1:3] = analysis
    Label(controls[1, 1:3], "实验参数", font = :bold, halign = :left, color = :white)
    Label(analysis[1, 1], "实时分析", font = :bold, halign = :left, color = :white)

    rowsize!(figure.layout, 1, 48)
    rowsize!(figure.layout, 2, 330)
    rowsize!(figure.layout, 3, 190)
    rowsize!(figure.layout, 4, 105)
    colsize!(figure.layout, 1, Relative(0.40))
    colsize!(figure.layout, 2, Relative(0.30))
    colsize!(figure.layout, 3, Relative(0.30))
    rowgap!(figure.layout, 8)
    return figure, wave_axis, trajectory_axis, auxiliary_axis, controls, analysis
end

function add_slider(grid, row, label, values, startvalue, formatter)
    Label(grid[row, 1], label, halign = :right)
    slider = Makie.Slider(
        grid[row, 2],
        range = values,
        startvalue = startvalue,
        update_while_dragging = true,
    )
    Label(grid[row, 3], lift(formatter, slider.value), halign = :left)
    rowsize!(grid, row, 31)
    return slider
end

function add_metrics(analysis, metrics, detail)
    for (column, metric) in enumerate(metrics)
        Label(analysis[2, column], metric, halign = :left)
        colsize!(analysis, column, Relative(0.25))
    end
    Label(analysis[3, 1:4], detail, halign = :left, color = MUTED)
end

function experiment_export_directory()
    configured = strip(get(ENV, "LISSAJOUS_EXPORT_DIR", ""))
    if !isempty(configured)
        return normpath(abspath(configured))
    end
    return normpath(
        joinpath(
            homedir(),
            "Documents",
            "物理实验助教",
            "实验导出",
            "李萨如图形",
        ),
    )
end

function unique_export_path(directory, prefix; extension = ".csv")
    timestamp = Dates.format(now(), "yyyymmdd_HHMMSS_sss")
    candidate = joinpath(directory, "$(prefix)_$(timestamp)$(extension)")
    counter = 1
    while isfile(candidate)
        candidate = joinpath(directory, "$(prefix)_$(timestamp)_$(counter)$(extension)")
        counter += 1
    end
    return candidate
end

function csv_field(value)
    text = value isa AbstractFloat ? @sprintf("%.12g", value) : string(value)
    if any(character -> character in (',', '"', '\n', '\r'), text)
        escaped = replace(text, "\"" => "\"\"")
        return "\"$(escaped)\""
    end
    return text
end

function write_experiment_csv(path, metadata, headers, columns)
    lengths = length.(columns)
    isempty(lengths) && error("CSV 至少需要一列数据。")
    all(==(first(lengths)), lengths) || error("CSV 各列长度不一致。")
    open(path, "w") do io
        write(io, UInt8[0xef, 0xbb, 0xbf])
        println(io, "# 李萨如图形可视化实验")
        for (key, value) in metadata
            println(io, "# $(key)=$(value)")
        end
        println(io, join(headers, ','))
        for row in 1:first(lengths)
            println(io, join((csv_field(column[row]) for column in columns), ','))
        end
    end
    return path
end

function write_experiment_csv_atomic(path, metadata, headers, columns)
    temporary = "$(path).partial-$(time_ns())"
    try
        write_experiment_csv(temporary, metadata, headers, columns)
        mv(temporary, path; force = false)
    finally
        isfile(temporary) && rm(temporary; force = true)
    end
    return path
end

function phase_csv_payload(current, amplitude, frequency, phase_degree, progress)
    metadata = [
        "experiment" => "phase",
        "amplitude" => Float64(amplitude),
        "frequency_hz" => Float64(frequency),
        "phase_deg" => Int(phase_degree),
        "progress_percent" => Float64(progress) / 10,
        "shape" => shape_name(current.phi),
        "direction" => rotation_name(current.phi),
        "semimajor_axis" => current.axes[1],
        "semiminor_axis" => current.axes[2],
        "period_s" => current.period,
    ]
    headers = ["sample_index", "u", "time_s", "x", "y"]
    columns = (
        collect(0:(length(current.u) - 1)),
        current.u,
        current.u .* current.period,
        current.x,
        current.y,
    )
    return (; metadata, headers, columns)
end

function amplitude_csv_payload(current, amplitude_x, amplitude_y, phase_degree, progress)
    a = Float64(amplitude_x)
    b = Float64(amplitude_y)
    metadata = [
        "experiment" => "amplitude",
        "amplitude_x" => a,
        "amplitude_y" => b,
        "amplitude_ratio_y_x" => current.ratio,
        "phase_deg" => Int(phase_degree),
        "progress_percent" => Float64(progress) / 10,
        "semimajor_axis" => current.axes[1],
        "semiminor_axis" => current.axes[2],
        "ellipse_area" => current.area,
        "trajectory_width" => 2 * maximum(abs, current.x),
        "trajectory_height" => 2 * maximum(abs, current.y),
    ]
    headers = ["sample_index", "u", "x", "y", "x_over_A", "y_over_B"]
    columns = (
        collect(0:(length(current.u) - 1)),
        current.u,
        current.x,
        current.y,
        current.x ./ a,
        current.y ./ b,
    )
    return (; metadata, headers, columns)
end

function ratio_csv_payload(current, base_frequency, m_value, n_value, phase_degree, progress)
    f0 = Float64(base_frequency)
    m = Int(m_value)
    n = Int(n_value)
    metadata = [
        "experiment" => "ratio",
        "base_frequency_hz" => f0,
        "m" => m,
        "n" => n,
        "gcd" => gcd(m, n),
        "reduced_m" => current.reduced_m,
        "reduced_n" => current.reduced_n,
        "frequency_x_hz" => current.frequency_x,
        "frequency_y_hz" => current.frequency_y,
        "phase_deg" => Int(phase_degree),
        "progress_percent" => Float64(progress) / 10,
        "close_period_s" => current.close_period,
        "endpoint_error" => current.endpoint_error,
    ]
    headers = ["sample_index", "u", "time_s", "x", "y", "distance_to_start"]
    columns = (
        collect(0:(length(current.u) - 1)),
        current.u,
        current.u .* current.close_period,
        current.x,
        current.y,
        current.distance,
    )
    return (; metadata, headers, columns)
end

function detune_csv_payload(
    current,
    amplitude,
    frequency,
    delta_frequency,
    phase_degree,
    progress,
)
    delta = Float64(delta_frequency)
    initial_phase = deg2rad(Float64(phase_degree))
    metadata = [
        "experiment" => "detune",
        "amplitude" => Float64(amplitude),
        "frequency_x_hz" => Float64(frequency),
        "delta_frequency_hz" => delta,
        "frequency_y_hz" => current.frequency_y,
        "phase_0_deg" => Int(phase_degree),
        "progress_percent" => Float64(progress) / 10,
        "current_time_s" => current.current_time,
        "shape_period_s" => current.shape_period,
        "effective_phase_rad" => current.effective_phase,
    ]
    headers = [
        "sample_index",
        "u",
        "time_s",
        "x",
        "y",
        "relative_phase_rad",
    ]
    columns = (
        collect(0:(length(current.u) - 1)),
        current.u,
        current.local_time,
        current.x,
        current.y,
        mod.(TWO_PI .* delta .* current.local_time .+ initial_phase, TWO_PI),
    )
    return (; metadata, headers, columns)
end

function open_export_directory(directory)
    mkpath(directory)
    if Sys.iswindows()
        executable = joinpath(get(ENV, "WINDIR", raw"C:\Windows"), "explorer.exe")
        if !isfile(executable)
            executable = "explorer.exe"
        end
        run(Cmd([executable, directory]); wait = false)
    elseif Sys.isapple()
        run(Cmd(["open", directory]); wait = false)
    else
        run(Cmd(["xdg-open", directory]); wait = false)
    end
    return nothing
end

function display_path(path)
    return replace(path, '\\' => "\\\u200b", '/' => "/\u200b")
end

function attach_csv_export!(writer, grid, analysis, slug)
    output_dir = experiment_export_directory()
    export_button = Makie.Button(
        grid[2, 1],
        label = "导出 CSV",
        height = 31,
        buttoncolor = BUTTON_BG,
        labelcolor = :white,
    )
    open_button = Makie.Button(
        grid[2, 2],
        label = "打开导出文件夹",
        height = 31,
        buttoncolor = BUTTON_BG,
        labelcolor = :white,
    )
    status = Observable("CSV 保存位置：$(display_path(output_dir))")
    status_color = lift(
        text -> startswith(text, "导出失败") ? ACCENT_Y : startswith(text, "正在") ? ACCENT_MAJOR : ACCENT_MINOR,
        status,
    )
    Label(
        analysis[1, 2:4],
        status,
        color = status_color,
        fontsize = 12,
        halign = :left,
        valign = :center,
        tellwidth = false,
        word_wrap = true,
    )
    on(export_button.clicks) do _
        status[] = "正在导出 CSV..."
        yield()
        try
            mkpath(output_dir)
            path = unique_export_path(output_dir, "lissajous_$(slug)")
            writer(path)
            status[] = "已导出：$(basename(path))；CSV 保存位置：$(display_path(output_dir))"
        catch error
            status[] = "导出失败：$(sprint(showerror, error))"
        end
    end
    on(open_button.clicks) do _
        try
            open_export_directory(output_dir)
            status[] = "已打开导出文件夹；CSV 保存位置：$(display_path(output_dir))"
        catch error
            status[] = "导出失败：无法打开文件夹（$(sprint(showerror, error))）"
        end
    end
    return nothing
end

function bind_playback!(grid, progress_slider, reset_values)
    playing = Observable(false)
    play_button = Makie.Button(
        grid[1, 1],
        label = "播放",
        height = 31,
        buttoncolor = BUTTON_BG,
        labelcolor = :white,
    )
    reset_button = Makie.Button(
        grid[1, 2],
        label = "重置",
        height = 31,
        buttoncolor = BUTTON_BG,
        labelcolor = :white,
    )
    on(play_button.clicks) do _
        playing[] = !playing[]
        play_button.label[] = playing[] ? "暂停" : "播放"
        if playing[]
            @async begin
                while playing[]
                    current = progress_slider.value[]
                    next_value = current >= 1000 ? 0 : min(1000, current + 8)
                    set_close_to!(progress_slider, next_value)
                    sleep(0.03)
                end
            end
        end
    end
    on(reset_button.clicks) do _
        playing[] = false
        play_button.label[] = "播放"
        for (slider, value) in reset_values
            set_close_to!(slider, value)
        end
    end
    return nothing
end

function phase_figure()
    figure, wave_axis, trajectory_axis, auxiliary_axis, controls, analysis =
        base_layout("相位差", "相位扫描与椭圆半轴比", "φ / degree", "b/a")
    parameter_grid = GridLayout()
    motion_grid = GridLayout()
    controls[2, 1:2] = parameter_grid
    controls[2, 3] = motion_grid

    amplitude = add_slider(parameter_grid, 1, "共同振幅 A", 0.2:0.05:2.0, 1.0, x -> @sprintf("%.2f", x))
    frequency = add_slider(parameter_grid, 2, "共同频率 f", 0.5:0.1:5.0, 1.0, x -> @sprintf("%.2f Hz", x))
    phase = add_slider(parameter_grid, 3, "相位差 φ", 0:1:360, 60, x -> @sprintf("%d°", x))
    progress = add_slider(parameter_grid, 4, "运动进程", 0:1:1000, 0, x -> @sprintf("%.1f%%", x / 10))

    data = lift(amplitude.value, frequency.value, phase.value) do a, f, degree
        u = collect(range(0.0, 1.0; length = 1001))
        theta = TWO_PI .* u
        phi = deg2rad(degree)
        x = a .* sin.(theta)
        y = a .* sin.(theta .+ phi)
        axes, _ = ellipse_geometry(a, a, phi)
        return (; u, x, y, trajectory = Point2f.(x, y), axes, phi, period = inv(f))
    end
    index = lift(progress.value, data) do value, current
        clamp(round(Int, value / 1000 * (length(current.u) - 1)) + 1, 1, length(current.u))
    end
    trace = lift(data, index) do current, i
        current.trajectory[1:i]
    end
    point = lift(data, index) do current, i
        Point2f[current.trajectory[i]]
    end

    lines!(wave_axis, lift(x -> x.u, data), lift(x -> x.x, data), color = ACCENT_X, linewidth = 2.4, label = "x")
    lines!(wave_axis, lift(x -> x.u, data), lift(x -> x.y, data), color = ACCENT_Y, linewidth = 2.4, label = "y")
    lines!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], -2.2), Point2f(current.u[i], 2.2)]
    end, color = (:white, 0.38), linewidth = 1.4, linestyle = :dash)
    scatter!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], current.x[i])]
    end, color = ACCENT_X, markersize = 12, strokecolor = :white)
    scatter!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], current.y[i])]
    end, color = ACCENT_Y, markersize = 12, strokecolor = :white)
    axislegend(wave_axis, position = :rt, framevisible = false)
    lines!(trajectory_axis, lift(x -> x.trajectory, data), color = (:white, 0.25), linewidth = 1.6)
    lines!(trajectory_axis, trace, color = ACCENT_MAJOR, linewidth = 3.6)
    scatter!(trajectory_axis, point, color = ACCENT_Y, markersize = 15, strokecolor = :white)

    degrees = collect(0.0:1.0:360.0)
    axis_ratio = map(degrees) do degree
        values, _ = ellipse_geometry(1.0, 1.0, deg2rad(degree))
        values[1] < 1.0e-12 ? 0.0 : values[2] / values[1]
    end
    lines!(auxiliary_axis, degrees, axis_ratio, color = ACCENT_X, linewidth = 2.5)
    ratio_point = lift(data, phase.value) do current, degree
        Point2f[Point2f(degree, current.axes[2] / max(current.axes[1], eps()))]
    end
    scatter!(auxiliary_axis, ratio_point, color = ACCENT_Y, markersize = 14, label = "设定相位")
    scan_point = lift(progress.value) do value
        degree = value / 1000 * 360
        values, _ = ellipse_geometry(1.0, 1.0, deg2rad(degree))
        ratio = values[1] < 1.0e-12 ? 0.0 : values[2] / values[1]
        Point2f[Point2f(degree, ratio)]
    end
    scatter!(
        auxiliary_axis,
        scan_point,
        color = ACCENT_MAJOR,
        markersize = 12,
        strokecolor = :white,
        label = "扫描相位",
    )
    axislegend(auxiliary_axis, position = :rt, framevisible = false)

    xlims!(wave_axis, 0, 1)
    ylims!(wave_axis, -2.2, 2.2)
    limits!(trajectory_axis, -2.2, 2.2, -2.2, 2.2)
    limits!(auxiliary_axis, 0, 360, -0.05, 1.05)

    metrics = (
        lift(x -> "形状：$(shape_name(x.phi))", data),
        lift(x -> "方向：$(rotation_name(x.phi))", data),
        lift(x -> @sprintf("半轴：%.3f / %.3f", x.axes[1], x.axes[2]), data),
        lift(x -> @sprintf("周期：%.3f s", x.period), data),
    )
    detail = lift(phase.value) do degree
        conjugate = mod(360 - degree, 360)
        "静态轨迹不能区分 φ = $(degree)° 与 φ = $(conjugate)°，运动方向可消除这一歧义。"
    end
    add_metrics(analysis, metrics, detail)
    bind_playback!(motion_grid, progress, [(amplitude, 1.0), (frequency, 1.0), (phase, 60), (progress, 0)])
    attach_csv_export!(motion_grid, analysis, "phase") do path
        current = data[]
        payload = phase_csv_payload(
            current,
            amplitude.value[],
            frequency.value[],
            phase.value[],
            progress.value[],
        )
        write_experiment_csv_atomic(path, payload.metadata, payload.headers, payload.columns)
    end
    return figure
end

function amplitude_figure()
    figure, wave_axis, trajectory_axis, auxiliary_axis, controls, analysis =
        base_layout("振幅比", "振幅归一化轨迹", "x/A", "y/B")
    parameter_grid = GridLayout()
    motion_grid = GridLayout()
    controls[2, 1:2] = parameter_grid
    controls[2, 3] = motion_grid

    amplitude_x = add_slider(parameter_grid, 1, "X 振幅 A", 0.2:0.05:2.0, 1.0, x -> @sprintf("%.2f", x))
    amplitude_y = add_slider(parameter_grid, 2, "Y 振幅 B", 0.2:0.05:2.0, 0.65, x -> @sprintf("%.2f", x))
    phase = add_slider(parameter_grid, 3, "相位差 φ", 0:1:360, 60, x -> @sprintf("%d°", x))
    progress = add_slider(parameter_grid, 4, "运动进程", 0:1:1000, 0, x -> @sprintf("%.1f%%", x / 10))

    data = lift(amplitude_x.value, amplitude_y.value, phase.value) do a, b, degree
        u = collect(range(0.0, 1.0; length = 1001))
        phi = deg2rad(degree)
        x = a .* sin.(TWO_PI .* u)
        y = b .* sin.(TWO_PI .* u .+ phi)
        axes, _ = ellipse_geometry(a, b, phi)
        return (;
            u,
            x,
            y,
            trajectory = Point2f.(x, y),
            normalized = Point2f.(x ./ a, y ./ b),
            axes,
            area = pi * a * b * abs(sin(phi)),
            ratio = b / a,
        )
    end
    index = lift(progress.value, data) do value, current
        clamp(round(Int, value / 1000 * 1000) + 1, 1, length(current.u))
    end
    trace = lift(data, index) do current, i
        current.trajectory[1:i]
    end
    point = lift(data, index) do current, i
        Point2f[current.trajectory[i]]
    end

    lines!(wave_axis, lift(x -> x.u, data), lift(x -> x.x, data), color = ACCENT_X, linewidth = 2.4, label = "x")
    lines!(wave_axis, lift(x -> x.u, data), lift(x -> x.y, data), color = ACCENT_Y, linewidth = 2.4, label = "y")
    lines!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], -2.2), Point2f(current.u[i], 2.2)]
    end, color = (:white, 0.38), linewidth = 1.4, linestyle = :dash)
    scatter!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], current.x[i])]
    end, color = ACCENT_X, markersize = 12, strokecolor = :white)
    scatter!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], current.y[i])]
    end, color = ACCENT_Y, markersize = 12, strokecolor = :white)
    axislegend(wave_axis, position = :rt, framevisible = false)
    lines!(trajectory_axis, lift(x -> x.trajectory, data), color = (:white, 0.25), linewidth = 1.6)
    lines!(trajectory_axis, trace, color = ACCENT_MAJOR, linewidth = 3.6)
    scatter!(trajectory_axis, point, color = ACCENT_Y, markersize = 15, strokecolor = :white)
    lines!(auxiliary_axis, lift(x -> x.normalized, data), color = ACCENT_MINOR, linewidth = 3)
    scatter!(auxiliary_axis, lift(data, index) do current, i
        Point2f[current.normalized[i]]
    end, color = ACCENT_Y, markersize = 14)

    xlims!(wave_axis, 0, 1)
    ylims!(wave_axis, -2.2, 2.2)
    limits!(trajectory_axis, -2.2, 2.2, -2.2, 2.2)
    limits!(auxiliary_axis, -1.15, 1.15, -1.15, 1.15)

    metrics = (
        lift(x -> @sprintf("B/A = %.3f", x.ratio), data),
        lift(x -> @sprintf("宽 = %.3f", 2 * maximum(abs, x.x)), data),
        lift(x -> @sprintf("高 = %.3f", 2 * maximum(abs, x.y)), data),
        lift(x -> @sprintf("椭圆面积 = %.4f", x.area), data),
    )
    detail = Observable("原始轨迹的宽高随振幅比改变；归一化后只保留相位关系。")
    add_metrics(analysis, metrics, detail)
    bind_playback!(motion_grid, progress, [(amplitude_x, 1.0), (amplitude_y, 0.65), (phase, 60), (progress, 0)])
    attach_csv_export!(motion_grid, analysis, "amplitude") do path
        current = data[]
        payload = amplitude_csv_payload(
            current,
            amplitude_x.value[],
            amplitude_y.value[],
            phase.value[],
            progress.value[],
        )
        write_experiment_csv_atomic(path, payload.metadata, payload.headers, payload.columns)
    end
    return figure
end

function ratio_figure()
    figure, wave_axis, trajectory_axis, auxiliary_axis, controls, analysis =
        base_layout("有理频率比", "轨迹返回起点的距离", "t / Tclose", "d(t)")
    parameter_grid = GridLayout()
    motion_grid = GridLayout()
    controls[2, 1:2] = parameter_grid
    controls[2, 3] = motion_grid

    base_frequency = add_slider(parameter_grid, 1, "基频 f₀", 0.5:0.1:5.0, 1.0, x -> @sprintf("%.2f Hz", x))
    m_slider = add_slider(parameter_grid, 2, "X 频率整数 m", 1:1:6, 2, x -> string(x))
    n_slider = add_slider(parameter_grid, 3, "Y 频率整数 n", 1:1:6, 3, x -> string(x))
    phase = add_slider(parameter_grid, 4, "初相位 φ", 0:1:360, 30, x -> @sprintf("%d°", x))
    progress = add_slider(parameter_grid, 5, "闭合进程", 0:1:1000, 0, x -> @sprintf("%.1f%%", x / 10))

    data = lift(base_frequency.value, m_slider.value, n_slider.value, phase.value) do f0, m, n, degree
        divisor = gcd(m, n)
        reduced_m = m ÷ divisor
        reduced_n = n ÷ divisor
        u = collect(range(0.0, 1.0; length = 1601))
        x = sin.(TWO_PI .* reduced_m .* u)
        y = sin.(TWO_PI .* reduced_n .* u .+ deg2rad(degree))
        distance = sqrt.((x .- first(x)) .^ 2 .+ (y .- first(y)) .^ 2)
        return (;
            u,
            x,
            y,
            trajectory = Point2f.(x, y),
            distance,
            reduced_m,
            reduced_n,
            frequency_x = m * f0,
            frequency_y = n * f0,
            close_period = inv(divisor * f0),
            endpoint_error = last(distance),
        )
    end
    index = lift(progress.value, data) do value, current
        clamp(round(Int, value / 1000 * (length(current.u) - 1)) + 1, 1, length(current.u))
    end
    trace = lift(data, index) do current, i
        current.trajectory[1:i]
    end

    lines!(wave_axis, lift(x -> x.u, data), lift(x -> x.x, data), color = ACCENT_X, linewidth = 2.2, label = "x")
    lines!(wave_axis, lift(x -> x.u, data), lift(x -> x.y, data), color = ACCENT_Y, linewidth = 2.2, label = "y")
    lines!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], -1.2), Point2f(current.u[i], 1.2)]
    end, color = (:white, 0.38), linewidth = 1.4, linestyle = :dash)
    scatter!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], current.x[i])]
    end, color = ACCENT_X, markersize = 11, strokecolor = :white)
    scatter!(wave_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], current.y[i])]
    end, color = ACCENT_Y, markersize = 11, strokecolor = :white)
    axislegend(wave_axis, position = :rt, framevisible = false)
    lines!(trajectory_axis, lift(x -> x.trajectory, data), color = (:white, 0.25), linewidth = 1.5)
    lines!(trajectory_axis, trace, color = ACCENT_MAJOR, linewidth = 3.4)
    scatter!(trajectory_axis, lift(data, index) do current, i
        Point2f[current.trajectory[i]]
    end, color = ACCENT_Y, markersize = 14, strokecolor = :white)
    lines!(auxiliary_axis, lift(x -> x.u, data), lift(x -> x.distance, data), color = ACCENT_X, linewidth = 2.5)
    scatter!(auxiliary_axis, lift(data, index) do current, i
        Point2f[Point2f(current.u[i], current.distance[i])]
    end, color = ACCENT_Y, markersize = 13)

    xlims!(wave_axis, 0, 1)
    ylims!(wave_axis, -1.2, 1.2)
    limits!(trajectory_axis, -1.15, 1.15, -1.15, 1.15)
    limits!(auxiliary_axis, 0, 1, -0.05, 2.95)

    metrics = (
        lift(x -> "约分频率比：$(x.reduced_m):$(x.reduced_n)", data),
        lift(x -> @sprintf("fx = %.2f Hz", x.frequency_x), data),
        lift(x -> @sprintf("fy = %.2f Hz", x.frequency_y), data),
        lift(x -> @sprintf("Tclose = %.4f s", x.close_period), data),
    )
    detail = lift(data, progress.value) do current, value
        value >= 999 ?
            @sprintf("闭合完成，终点误差 %.2e。", current.endpoint_error) :
            "彩色轨迹表示当前闭合进程，右图显示轨迹到起点的距离。"
    end
    add_metrics(analysis, metrics, detail)
    bind_playback!(motion_grid, progress, [(base_frequency, 1.0), (m_slider, 2), (n_slider, 3), (phase, 30), (progress, 0)])
    attach_csv_export!(motion_grid, analysis, "ratio") do path
        current = data[]
        payload = ratio_csv_payload(
            current,
            base_frequency.value[],
            m_slider.value[],
            n_slider.value[],
            phase.value[],
            progress.value[],
        )
        write_experiment_csv_atomic(path, payload.metadata, payload.headers, payload.columns)
    end
    return figure
end

function detune_figure()
    figure, wave_axis, trajectory_axis, auxiliary_axis, controls, analysis =
        base_layout("频率失谐", "等效相位累积", "t / Tshape", "Δφ / 2π")
    parameter_grid = GridLayout()
    motion_grid = GridLayout()
    controls[2, 1:2] = parameter_grid
    controls[2, 3] = motion_grid

    amplitude = add_slider(parameter_grid, 1, "共同振幅 A", 0.2:0.05:2.0, 1.0, x -> @sprintf("%.2f", x))
    frequency = add_slider(parameter_grid, 2, "X 频率 f", 0.5:0.1:5.0, 1.0, x -> @sprintf("%.2f Hz", x))
    delta_frequency = add_slider(parameter_grid, 3, "频率差 Δf", -0.4:0.01:0.4, 0.05, x -> @sprintf("%+.2f Hz", x))
    phase = add_slider(parameter_grid, 4, "初相位 φ₀", 0:1:360, 30, x -> @sprintf("%d°", x))
    progress = add_slider(parameter_grid, 5, "形变进程", 0:1:1000, 0, x -> @sprintf("%.1f%%", x / 10))

    data = lift(amplitude.value, frequency.value, delta_frequency.value, phase.value, progress.value) do a, f, delta, degree, value
        phi0 = deg2rad(degree)
        shape_period = abs(delta) < 1.0e-12 ? Inf : inv(abs(delta))
        span = isfinite(shape_period) ? shape_period : 2 * inv(f)
        current_time = value / 1000 * span
        local_time = collect(range(current_time - inv(f), current_time; length = 1001))
        u = collect(range(0.0, 1.0; length = 1001))
        x = a .* sin.(TWO_PI .* f .* local_time)
        y = a .* sin.(TWO_PI .* (f + delta) .* local_time .+ phi0)
        effective_phase = mod(TWO_PI * delta * current_time + phi0, TWO_PI)
        phase_curve = phi0 / TWO_PI .+ delta .* collect(range(0.0, span; length = 1001))
        return (;
            u,
            local_time,
            current_time,
            x,
            y,
            trajectory = Point2f.(x, y),
            shape_period,
            effective_phase,
            phase_curve,
            frequency_y = f + delta,
        )
    end
    trace_index = 760

    lines!(wave_axis, lift(x -> x.u, data), lift(x -> x.x, data), color = ACCENT_X, linewidth = 2.3, label = "x")
    lines!(wave_axis, lift(x -> x.u, data), lift(x -> x.y, data), color = ACCENT_Y, linewidth = 2.3, label = "y")
    axislegend(wave_axis, position = :rt, framevisible = false)
    lines!(trajectory_axis, lift(x -> x.trajectory, data), color = (:white, 0.25), linewidth = 1.6)
    lines!(trajectory_axis, lift(x -> x.trajectory[1:trace_index], data), color = ACCENT_MAJOR, linewidth = 3.5)
    scatter!(trajectory_axis, lift(x -> Point2f[x.trajectory[trace_index]], data), color = ACCENT_Y, markersize = 14, strokecolor = :white)
    lines!(auxiliary_axis, lift(x -> x.u, data), lift(x -> x.phase_curve, data), color = ACCENT_MAJOR, linewidth = 2.5)
    scatter!(auxiliary_axis, lift(data, progress.value) do current, value
        i = clamp(round(Int, value / 1000 * 1000) + 1, 1, 1001)
        Point2f[Point2f(value / 1000, current.phase_curve[i])]
    end, color = ACCENT_Y, markersize = 13)

    xlims!(wave_axis, 0, 1)
    ylims!(wave_axis, -2.2, 2.2)
    limits!(trajectory_axis, -2.2, 2.2, -2.2, 2.2)
    limits!(auxiliary_axis, 0, 1, -1.25, 2.25)

    metrics = (
        lift(x -> @sprintf("fx = %.2f Hz", x), frequency.value),
        lift(x -> @sprintf("fy = %.2f Hz", x.frequency_y), data),
        lift(x -> isfinite(x.shape_period) ? @sprintf("Tshape = %.3f s", x.shape_period) : "Tshape = ∞", data),
        lift(x -> @sprintf("等效相位 = %.1f°", rad2deg(x.effective_phase)), data),
    )
    detail = Observable("频率差使相位持续累积；形变进程完成一周时，相对相位改变 2π。")
    add_metrics(analysis, metrics, detail)
    bind_playback!(motion_grid, progress, [(amplitude, 1.0), (frequency, 1.0), (delta_frequency, 0.05), (phase, 30), (progress, 0)])
    attach_csv_export!(motion_grid, analysis, "detune") do path
        current = data[]
        payload = detune_csv_payload(
            current,
            amplitude.value[],
            frequency.value[],
            delta_frequency.value[],
            phase.value[],
            progress.value[],
        )
        write_experiment_csv_atomic(path, payload.metadata, payload.headers, payload.columns)
    end
    return figure
end

const PAGE_STYLE = """
html, body { margin: 0; min-height: 100%; background: #0b0f14; color: #eef3f8; }
body { overflow-x: auto; font-family: 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif; }
.lab-page { min-width: 960px; min-height: 760px; padding: 8px; box-sizing: border-box; background: #0b0f14; }
.wglmakie-spinner {
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
body:has(.wglmakie-spinner)::before {
    content: "正在初始化 Julia / WGLMakie / Bonito 交互图形";
    position: fixed;
    left: 50%;
    top: calc(50% + 54px);
    z-index: 1001;
    width: min(520px, calc(100vw - 48px));
    color: #c9d7e4;
    font-size: 16px;
    line-height: 1.6;
    text-align: center;
    transform: translateX(-50%);
    pointer-events: none;
}
.lissajous-diagnostic {
    position: fixed;
    left: 16px;
    right: 16px;
    bottom: 16px;
    z-index: 1002;
    display: none;
    padding: 10px 12px;
    color: #f7d7d7;
    background: rgba(64, 20, 28, .94);
    border: 1px solid rgba(255, 85, 105, .65);
    border-radius: 6px;
    font: 13px/1.5 ui-monospace, Consolas, monospace;
    white-space: pre-wrap;
}
.lissajous-diagnostic.visible { display: block; }
"""

const CLIENT_STATUS_SCRIPT = """
(() => {
    let finished = false;
    let slowSent = false;
    const parentWindow = window.parent || window;
    const send = (type, detail = "") => {
        parentWindow.postMessage({ type, detail }, "*");
    };
    const showDiagnostic = detail => {
        let box = document.getElementById("lissajous-diagnostic");
        if (!box) {
            box = document.createElement("div");
            box.id = "lissajous-diagnostic";
            box.className = "lissajous-diagnostic";
            document.body.appendChild(box);
        }
        box.textContent = detail;
        box.classList.add("visible");
    };
    const fail = detail => {
        if (finished) return;
        finished = true;
        showDiagnostic(detail);
        send("lissajous-wgl-failed", detail);
    };
    const webglProbe = () => {
        try {
            const canvas = document.createElement("canvas");
            const gl2 = canvas.getContext("webgl2", { antialias: true });
            if (gl2) return "webgl2";
            const gl1 = canvas.getContext("webgl", { antialias: true }) || canvas.getContext("experimental-webgl");
            if (gl1) return "webgl1";
        } catch (error) {
            return "error: " + error.message;
        }
        return "none";
    };
    const glStatus = webglProbe();
    if (glStatus === "none" || glStatus.startsWith("error:")) {
        fail("浏览器无法创建 WebGL 上下文：" + glStatus + "\\n请确认浏览器允许硬件加速，或使用程序自动打开的 Edge/Chrome 窗口。");
        return;
    }
    const startedAt = performance.now();
    const check = () => {
        if (finished) return;
        const canvas = document.querySelector("canvas");
        const spinner = document.querySelector(".wglmakie-spinner");
        if (canvas && !spinner) {
            finished = true;
            send("lissajous-wgl-ready", "canvas-ready; " + glStatus);
            return;
        }
        if (!slowSent && performance.now() - startedAt > 45000) {
            slowSent = true;
            send(
                "lissajous-wgl-slow",
                "首次启动可能超过 1 分钟，WGLMakie/Bonito 仍在初始化（" + glStatus + "），请继续等待。"
            );
        }
        window.setTimeout(check, 300);
    };
    window.addEventListener("error", event => {
        fail("浏览器脚本错误：" + event.message + "\\n" + event.filename + ":" + event.lineno);
    });
    window.addEventListener("unhandledrejection", event => {
        fail("浏览器 Promise 错误：" + String(event.reason));
    });
    check();
})();
"""

function experiment_app(title, builder)
    return Bonito.App(; title = title) do
        figure = builder()
        return DOM.div(
            DOM.style(PAGE_STYLE),
            DOM.div(figure; class = "lab-page"),
            DOM.script(CLIENT_STATUS_SCRIPT),
        )
    end
end

function index_app()
    links = [
        DOM.a(name; href = path, style = "color:#73d7cf;margin-right:24px")
        for (name, path) in (
            ("相位差", "/phase"),
            ("振幅比", "/amplitude"),
            ("有理频率比", "/ratio"),
            ("频率失谐", "/detune"),
        )
    ]
    return Bonito.App(
        DOM.div(
            DOM.style(PAGE_STYLE),
            DOM.h1("李萨如图形可视化实验"),
            DOM.div(links...),
            style = "padding:32px;background:#0b0f14;color:#eef3f8;min-height:100vh",
        );
        title = "李萨如图形可视化实验",
    )
end

function run_csv_export_self_test()
    u = [0.0, 0.5, 1.0]
    phase_current = (;
        u,
        x = [0.0, 1.0, 0.0],
        y = [1.0, 0.0, -1.0],
        axes = [1.0, 1.0],
        phi = pi / 2,
        period = 0.5,
    )
    amplitude_current = (;
        u,
        x = [0.0, 1.0, 0.0],
        y = [0.5, 0.0, -0.5],
        axes = [1.0, 0.5],
        area = pi / 2,
        ratio = 0.5,
    )
    ratio_current = (;
        u,
        x = [0.0, 0.0, 0.0],
        y = [0.5, -0.5, 0.5],
        distance = [0.0, 1.0, 0.0],
        reduced_m = 2,
        reduced_n = 3,
        frequency_x = 2.0,
        frequency_y = 3.0,
        close_period = 1.0,
        endpoint_error = 0.0,
    )
    initial_phase = pi / 6
    local_time = [4.0, 4.5, 5.0]
    detune_current = (;
        u,
        local_time,
        x = sin.(TWO_PI .* local_time),
        y = sin.(TWO_PI .* 1.1 .* local_time .+ initial_phase),
        frequency_y = 1.1,
        current_time = 5.0,
        shape_period = 10.0,
        effective_phase = mod(TWO_PI * 0.1 * 5.0 + initial_phase, TWO_PI),
    )
    payloads = (
        "phase" => phase_csv_payload(phase_current, 1.0, 2.0, 90, 500),
        "amplitude" => amplitude_csv_payload(amplitude_current, 1.0, 0.5, 90, 500),
        "ratio" => ratio_csv_payload(ratio_current, 1.0, 2, 3, 30, 500),
        "detune" => detune_csv_payload(detune_current, 1.0, 1.0, 0.1, 30, 500),
    )
    expected_headers = Dict(
        "phase" => "sample_index,u,time_s,x,y",
        "amplitude" => "sample_index,u,x,y,x_over_A,y_over_B",
        "ratio" => "sample_index,u,time_s,x,y,distance_to_start",
        "detune" => "sample_index,u,time_s,x,y,relative_phase_rad",
    )
    mktempdir() do directory
        for (slug, payload) in payloads
            path = joinpath(directory, "$(slug).csv")
            write_experiment_csv_atomic(
                path,
                payload.metadata,
                payload.headers,
                payload.columns,
            )
            bytes = read(path)
            @assert length(bytes) > 3
            @assert bytes[1:3] == UInt8[0xef, 0xbb, 0xbf]
            lines = split(read(path, String), '\n'; keepempty = false)
            header_index = findfirst(==(expected_headers[slug]), lines)
            @assert !isnothing(header_index)
            @assert length(lines) - header_index == length(u)
            @assert occursin("# experiment=$(slug)", String(bytes[4:end]))
            @assert occursin("# progress_percent=50", String(bytes[4:end]))
        end
        first_path = unique_export_path(directory, "collision")
        touch(first_path)
        second_path = unique_export_path(directory, "collision")
        @assert first_path != second_path
        @assert isempty(filter(path -> occursin(".partial-", path), readdir(directory)))
    end
    expected_relative_phase = mod(TWO_PI * 0.1 * first(local_time) + initial_phase, TWO_PI)
    detune_phase_column = payloads[4].second.columns[6]
    @assert isapprox(first(detune_phase_column), expected_relative_phase; atol = 1.0e-12)
    @assert all(value -> 0.0 <= value < TWO_PI, detune_phase_column)
    println("四路由 CSV 导出自检通过：BOM、表头、行数、唯一命名和失谐相位均正常。")
end

function run_self_test()
    axes, _ = ellipse_geometry(1.0, 1.0, pi / 2)
    @assert isapprox(axes[1], 1.0; atol = 1.0e-10)
    @assert isapprox(axes[2], 1.0; atol = 1.0e-10)
    @assert shape_name(0.0) == "正斜率直线"
    @assert shape_name(pi / 2) == "圆"
    for builder in (phase_figure, amplitude_figure, ratio_figure, detune_figure)
        figure = builder()
        @assert figure isa Figure
    end
    run_csv_export_self_test()
    println("四个独立网页实验自检通过。")
end

function main()
    load_packaged_wgl_shaders!()
    WGLMakie.activate!(; use_html_widgets = true)
    configure_theme!()
    if "--self-test" in ARGS
        run_self_test()
        return
    end
    host = get(ENV, "LISSAJOUS_WEB_HOST", "127.0.0.1")
    port = parse(Int, get(ENV, "LISSAJOUS_WEB_PORT", "9384"))
    browser_host = get(ENV, "LISSAJOUS_WEB_BROWSER_HOST", "127.0.0.1")
    server = Bonito.Server(host, port; proxy_url = "http://$(browser_host):$(port)")
    Bonito.route!(server, "/" => index_app())
    Bonito.route!(server, "/phase" => experiment_app("相位差", phase_figure))
    Bonito.route!(server, "/amplitude" => experiment_app("振幅比", amplitude_figure))
    Bonito.route!(server, "/ratio" => experiment_app("有理频率比", ratio_figure))
    Bonito.route!(server, "/detune" => experiment_app("频率失谐", detune_figure))
    println("李萨如图形网页实验已启动：http://$(host):$(port)")
    wait(server)
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
