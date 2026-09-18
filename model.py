# a=input("输入手机号码：")
# b=input("学号：")
# c=int(input("商品数量："))
# d=float(input("商品单价："))
# print("手机号码是：",a)
# print("学号是：",b)
# print("商品数量是：",c)
# print("商品单价是：",d)
# print("总价是",c*d)
# a=[]78
# for i in range(5):
#     number=input('请输入你的分数')78
#     a.append(number)
#78
# print(a)
import statistics

classnumber=int (input("本班人数"))
nuber=[]
names=[]
t1=0
t2=0
for i in range(classnumber):
    name=(input("姓名："))
    a = int(input("分数："))
    if a > 100 or a<0 :
        print("分数不存在")

    else:
        if a>=60 :
            print("合格")
            t1+=1

        if a<=60 :
            print("你没合格")
            t2+=1
    nuber.append(a)
    names.append(name)

print(nuber)
print("合格",t1,"人")
print("不合格",t2,"人")
print("平均分；",sum(nuber)/len(nuber))
print("总分",sum(nuber))
print("成绩的方差",statistics.variance(nuber))
print("---------- 成绩单 ----------")
for name, score in zip(names, nuber):
    result = "合格" if score >= 60 else "不合格"
    print(f"{name}：{score}分 —— {result}")




