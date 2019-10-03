def undo_logic():
    # TODO 补全逻辑
    print(
'''
撤销操作的逻辑如下：
1.编辑模式下
    恢复到上一次标记状态被备份时
    如果没有标记状态备份，return
2.创建模式下
    如果有正在创建的标记，撤销其最后一个点
    如果标记已经创建完毕，撤销最后被创建的标记的最后一个点
    如果canvas上没有任何标记，
'''
    )

def creating_logic():
    print(
'''
一个标记的创建是这样完成的：
    整个周期在创建模式下进行，期间创建类型不改变
    通过鼠标左键点击开始绘制/增加点
    通过鼠标移动决定点的位置，期间显示连线
    通过撤销（ctrl+z）取消点
    通过完成（shift）完成一个标记的绘制
    标记创建的状态由current_annotation维护：
        在开始前和完成后，current_annotation都是None
        在创建过程中，current_annotation记录点，并且能被绘制
    标记创建过程的连线显示由current_line维护
'''
    )

if __name__ == '__main__':
    undo_logic()