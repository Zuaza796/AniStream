using System.Drawing.Drawing2D;
namespace AniStream.Fresa;

public static class Candy
{
    public static readonly Color Cream = Color.FromArgb(255, 247, 249);
    public static readonly Color Pink = Color.FromArgb(255, 218, 231);
    public static readonly Color Rose = Color.FromArgb(237, 137, 172);
    public static readonly Color Berry = Color.FromArgb(177, 74, 114);
    public static readonly Color Ink = Color.FromArgb(101, 57, 76);
    public static readonly Color Mint = Color.FromArgb(157, 199, 164);
    public static Font Font(float size = 10, FontStyle style = FontStyle.Regular) => new("Segoe UI", size, style);
}

/// <summary>Real strawberry-shaped hit region, not a rectangular button with a sticker.</summary>
public sealed class StrawberryButton : Button
{
    bool hover, pressed;
    [System.ComponentModel.DesignerSerializationVisibility(System.ComponentModel.DesignerSerializationVisibility.Hidden)]
    public string Glyph { get; set; } = "▶";
    public StrawberryButton(string glyph, string description, EventHandler? click = null)
    {
        Glyph = glyph; AccessibleName = description; AccessibleDescription = description;
        Text = description; Size = new(56, 64); FlatStyle = FlatStyle.Flat;
        FlatAppearance.BorderSize = 0; BackColor = Color.Transparent;
        Cursor = Cursors.Hand; TabStop = true; Margin = new(4);
        SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.SupportsTransparentBackColor | ControlStyles.ResizeRedraw, true);
        if (click != null) Click += click;
    }
    public static GraphicsPath BerryPath()
    {
        var p = new GraphicsPath();
        p.StartFigure(); p.AddBezier(50, 27, 20, 4, -5, 32, 13, 61);
        p.AddBezier(13, 61, 23, 79, 38, 96, 50, 101);
        p.AddBezier(50, 101, 62, 96, 77, 79, 87, 61);
        p.AddBezier(87, 61, 105, 32, 80, 4, 50, 27); p.CloseFigure();
        return p;
    }
    static GraphicsPath Leaves()
    {
        var p = new GraphicsPath();
        p.AddPolygon([new(49, 31), new(17, 18), new(35, 16), new(36, 1), new(51, 15), new(66, 1), new(66, 17), new(87, 16), new(62, 33), new(51, 22)]);
        return p;
    }
    protected override void OnResize(EventArgs e)
    {
        base.OnResize(e);
        if (Width <= 0 || Height <= 0) return;
        using var outline = BerryPath(); using var leaves = Leaves(); outline.AddPath(leaves, false);
        using var scale = new Matrix(Width / 100f, 0, 0, Height / 108f, 0, 0); outline.Transform(scale);
        var old = Region; Region = new Region(outline); old?.Dispose();
    }
    protected override void OnPaint(PaintEventArgs e)
    {
        var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
        g.ScaleTransform(Width / 100f, Height / 108f);
        if (pressed) g.TranslateTransform(0, 2);
        using var body = BerryPath();
        Color top = !Enabled ? Color.FromArgb(232, 202, 212) : hover ? Color.FromArgb(255, 167, 195) : Color.FromArgb(249, 188, 209);
        using var fill = new LinearGradientBrush(new Rectangle(0, 20, 100, 85), top, !Enabled ? Color.FromArgb(219, 186, 199) : Candy.Rose, 90);
        g.FillPath(fill, body);
        using var border = new Pen(!Enabled ? Color.FromArgb(215, 178, 192) : Candy.Berry, 2.2f); g.DrawPath(border, body);
        using var leaf = Leaves(); using var green = new SolidBrush(Candy.Mint); g.FillPath(green, leaf);
        using var leafBorder = new Pen(Color.FromArgb(112, 157, 120), 1.6f); g.DrawPath(leafBorder, leaf);
        using var seed = new SolidBrush(Color.FromArgb(255, 249, 217));
        foreach (var point in new Point[] { new(23, 35),new(76,35),new(17,49),new(82,49),new(28,69),new(71,69),new(39,84),new(60,84) })
            g.FillEllipse(seed, point.X, point.Y, 3.3f, 5);
        using var ink = new Pen(Color.White, 4) { StartCap = LineCap.Round, EndCap = LineCap.Round };
        if (Glyph == "search") { g.DrawEllipse(ink,31,37,25,25);g.DrawLine(ink,53,59,67,73); }
        else if (Glyph == "pip") { g.DrawRectangle(ink,27,39,46,30);using var white=new SolidBrush(Color.White);g.FillRectangle(white,49,53,18,12); }
        else if (Glyph == "home") { g.DrawLines(ink,[new(29,52),new(50,35),new(71,52)]);g.DrawLines(ink,[new(35,49),new(35,72),new(65,72),new(65,49)]); }
        else
        {
            using var glyphFont = new Font("Segoe UI Symbol", Glyph.Length > 2 ? 19 : 25, FontStyle.Bold, GraphicsUnit.Pixel);
            using var textBrush = new SolidBrush(Color.White);
            using var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center };
            g.DrawString(Glyph,glyphFont,textBrush,new RectangleF(12,32,76,47),sf);
        }
        if (Focused && ShowFocusCues) { using var focus=new Pen(Color.White,2){DashStyle=DashStyle.Dot};g.DrawPath(focus,body); }
    }
    protected override void OnMouseEnter(EventArgs e) { hover=true;Invalidate();base.OnMouseEnter(e); }
    protected override void OnMouseLeave(EventArgs e) { hover=false;pressed=false;Invalidate();base.OnMouseLeave(e); }
    protected override void OnMouseDown(MouseEventArgs e) { pressed=true;Invalidate();base.OnMouseDown(e); }
    protected override void OnMouseUp(MouseEventArgs e) { pressed=false;Invalidate();base.OnMouseUp(e); }
    protected override void OnGotFocus(EventArgs e) { Invalidate();base.OnGotFocus(e); }
    protected override void OnLostFocus(EventArgs e) { Invalidate();base.OnLostFocus(e); }
}
