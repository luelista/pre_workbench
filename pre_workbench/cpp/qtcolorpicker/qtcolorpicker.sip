%Module(name=qtcolorpicker, language="C++")

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip
%Import QtWidgets/QtWidgetsmod.sip

class QT_QTCOLORPICKER_EXPORT QtColorPicker : public QPushButton
{
%TypeHeaderCode
#include "qtcolorpicker.h"
%End

    Q_OBJECT

    Q_PROPERTY(bool colorDialog READ colorDialogEnabled WRITE setColorDialogEnabled)

public:
    QtColorPicker(QWidget *parent = 0,
                  int columns = -1, bool enableColorDialog = true);

    ~QtColorPicker();

    void insertColor(const QColor &color, const QString &text = QString::null, int index = -1);

    QColor currentColor() const;

    QColor color(int index) const;

    void setColorDialogEnabled(bool enabled);
    bool colorDialogEnabled() const;

    void setStandardColors();

    static QColor getColor(const QPoint &pos, bool allowCustomColors = true);

public Q_SLOTS:
    void setCurrentColor(const QColor &col);

Q_SIGNALS:
    void colorChanged(const QColor &);

protected:
    void paintEvent(QPaintEvent *e);

private Q_SLOTS:
    void buttonPressed(bool toggled);
    void popupClosed();

private:
    ColorPickerPopup *popup;
    QColor col;
    bool withColorDialog;
    bool dirty;
    bool firstInserted;
};


